import os
import json
import re
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

class KnowledgeEngine:
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = data_dir
        self.reload_all()

    def _load_json(self, filename, default=None):
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            return default if default is not None else {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return default if default is not None else {}

    def reload_all(self):
        """Reload all data files from disk so dynamic admin changes reflect immediately."""
        self.college_info = self._load_json("college_info.json")
        self.college_data = self._load_json("college_data.json")
        self.programmes = self._load_json("programmes.json")
        self.course_structure = self._load_json("course_structure.json")
        self.admissions = self._load_json("admissions.json")
        self.services = self._load_json("services.json")
        self.rules = self._load_json("rules.json")
        self.welfare = self._load_json("welfare.json")
        self.kaushal = self._load_json("kaushal.json")
        self.student_life = self._load_json("student_life.json")
        self.updates = self._load_json("updates.json", default={"updates": []})
        self.faqs = self._load_json("faqs.json", default={"faqs": []})

    def get_latest_updates(self, limit=None):
        updates_list = [u for u in self.updates.get("updates", []) if u.get("status") == "Active"]
        updates_list.sort(key=lambda x: x.get("date_added", ""), reverse=True)
        return updates_list[:limit] if limit else updates_list

    def search_all(self, query):
        """Global search across all knowledge domains dynamically."""
        if not query or len(query.strip()) < 2:
            return []
        
        q = query.lower().strip()
        tokens = re.findall(r'\w+', q)
        results = []

        def match_score(text):
            if not text:
                return 0
            t = str(text).lower()
            if q in t:
                return 10
            score = 0
            for token in tokens:
                if len(token) > 2 and token in t:
                    score += 2
            return score

        def generate_snippet(text):
            text_str = str(text).replace('\n', ' ')
            t = text_str.lower()
            idx = t.find(q)
            if idx == -1:
                for token in tokens:
                    if len(token) > 2:
                        idx = t.find(token)
                        if idx != -1:
                            break
            if idx == -1:
                return text_str[:140] + "..."
            start = max(0, idx - 60)
            end = min(len(text_str), idx + 80)
            snip = text_str[start:end]
            if start > 0: snip = "..." + snip
            if end < len(text_str): snip = snip + "..."
            return snip

        def traverse(data, path, current_category, current_title=None):
            if isinstance(data, dict):
                obj_title = data.get("title") or data.get("name") or data.get("question") or current_title
                for k, v in data.items():
                    traverse(v, path + [str(k)], current_category, obj_title)
            elif isinstance(data, list):
                for i, v in enumerate(data):
                    traverse(v, path, current_category, current_title)
            elif isinstance(data, str) and len(data) > 3:
                score = match_score(data)
                if score > 0:
                    readable_path = [p for p in path if not p.startswith("[") and p not in ["description", "content", "answer", "eligibility", "info", "information", "name", "title"]]
                    fallback_title = readable_path[-1].replace("_", " ").title() if readable_path else "Information"
                    title = current_title if current_title else fallback_title
                    
                    url = f"/{current_category.replace('_', '-')}"
                    if current_category == "college_data": url = "/"
                    elif current_category == "college_info": url = "/"
                    elif current_category == "course_structure": url = "/courses"
                    elif current_category == "faqs": url = "/#faq"
                    
                    results.append({
                        "title": title,
                        "category": current_category.replace("_", " ").title(),
                        "snippet": generate_snippet(data),
                        "url": url,
                        "source": "College Knowledge Base",
                        "score": score
                    })

        datasets = {
            "college_info": getattr(self, "college_info", {}),
            "college_data": getattr(self, "college_data", {}),
            "programmes": getattr(self, "programmes", {}),
            "course_structure": getattr(self, "course_structure", {}),
            "admissions": getattr(self, "admissions", {}),
            "services": getattr(self, "services", {}),
            "rules": getattr(self, "rules", {}),
            "welfare": getattr(self, "welfare", {}),
            "kaushal": getattr(self, "kaushal", {}),
            "student_life": getattr(self, "student_life", {}),
            "updates": getattr(self, "updates", {}),
            "faqs": getattr(self, "faqs", {})
        }
        
        for cat, data in datasets.items():
            traverse(data, [cat], cat)

        # Deduplicate and sort by score
        seen = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x["score"], reverse=True):
            if r["snippet"] not in seen:
                seen.add(r["snippet"])
                unique_results.append(r)

        return unique_results

    def answer_query(self, user_message):
        """Intelligently processes natural language user queries without hallucinating."""
        if not user_message or not user_message.strip():
            return {
                "reply": "Please ask a question regarding Vande Mataram Degree College programmes, admissions, attendance, fees, scholarships, or services.",
                "source": "System",
                "quick_actions": ["Courses", "Admission", "Eligibility", "Scholarships", "Services"]
            }

        q = user_message.lower().strip()
        self.reload_all()

        # Step 1: Check dynamic active updates if query explicitly references updates/portals/notices
        is_update_query = any(k in q for k in ["portal", "result", "notice", "announcement", "update", "latest news", "where can i check my result"])
        if is_update_query:
            for update in self.get_latest_updates():
                title = update.get("title", "").lower()
                content = update.get("content", "").lower()
                
                if ("result" in q and ("result" in title or "result" in content)) or \
                   ("portal" in q and ("portal" in title or "portal" in content)) or \
                   any(word in q for word in ["mahadbt", "xyz", "notice", "announcement"] if word in (title + content)):
                    reply = f"📢 **{update.get('title')}** ({update.get('category')} - {update.get('date_added')})\n\n{update.get('content')}"
                    if update.get("url"):
                        reply += f"\n\n🔗 [Official Portal Link]({update.get('url')})"
                    return {
                        "reply": reply,
                        "source": f"Latest Update ({update.get('source', 'College Office')})",
                        "quick_actions": ["More Updates", "Admissions", "Contact Office"]
                    }

        # Step 2: Specific high-precision services & entities FIRST
        # Bonafide Certificate
        if "bonafide" in q:
            bon = next((s for s in self.services["services"] if s["id"] == "bonafide_certificate"), {})
            reply = f"📄 **Bonafide Certificate Procedure (Turnaround: {bon.get('time_minutes', '05 mins')}):**\n\n" \
                    f"• **Regular Students:** Submit an application stating Student's Full Name, Address, Class, Roll Number, Date of Birth, and Academic Year (e.g. 2024-25).\n" \
                    f"• **Repeater Students:** Application + Attested photocopy of last year's mark sheet.\n\n" \
                    f"Submit the application at the college administrative office counter during working hours."
            return {"reply": reply, "source": "Handbook Extension Services (p. 15, 25)", "quick_actions": ["Railway Concession", "NOC", "Student Services"]}

        # Railway Concession
        if any(k in q for k in ["railway", "concession", "train pass", "season ticket", "kopar"]):
            rail = next((s for s in self.services["services"] if s["id"] == "railway_concession"), {})
            reply = f"🚆 **Railway Concession Procedure (Turnaround: {rail.get('time_minutes', '05 mins')}):**\n\n" \
                    f"• **Eligibility:** Bonafide students of the college below **25 years of age**.\n" \
                    f"• **Season Tickets:** Granted between the student's residence station and **Kopar station**.\n" \
                    f"• **Documents Required:** Prescribed application form + Attested photocopy of Ration Card or valid residence proof.\n" \
                    f"• **Timing:** Applications accepted between recess and after lectures on working days in the office.\n" \
                    f"• **Long Journey (Vacation):** Granted during vacation as per railway rules (inquire up to 3:00 PM)."
            return {"reply": reply, "source": "Handbook Extension Services & Rules (p. 15, 25)", "quick_actions": ["Bonafide Certificate", "Student Services", "Rules"]}

        # NSS (National Service Scheme)
        if "nss" in q or "national service scheme" in q:
            nss = self.student_life.get("nss", {})
            acts = ", ".join(nss.get("activities", []))
            reply = f"🤝 **National Service Scheme (NSS):**\n\n" \
                    f"• **Eligibility:** Degree college students.\n" \
                    f"• **Aim:** {nss.get('aim')}\n" \
                    f"• **Key Activities:** {acts}.\n" \
                    f"• **10 Grace Marks Benefit:** Students who satisfactorily complete **120 hours of NSS work** are eligible to get **10 grace marks** at the college / university examination!"
            return {"reply": reply, "source": "Handbook Student Life (p. 20)", "quick_actions": ["Student Council", "Gymkhana", "Activities", "Committees"]}

        # VMDC Kaushal Centre
        if any(k in q for k in ["kaushal", "klic", "skill centre", "skill course", "vocational course"]):
            courses = [f"• {c['name']}" for c in self.kaushal.get("courses", [])[:10]]
            reply = f"🛠️ **VMDC Kaushal Centre:**\n\n" \
                    f"• **Structure:** 20 Job-oriented KLiC certificate courses.\n" \
                    f"• **Duration:** 120 Hours per course.\n" \
                    f"• **Fee:** Rs. 6000/- per course.\n" \
                    f"• **Scholarship:** Deserving students may apply for **JMF Scholarship** to fund course fees.\n\n" \
                    f"**Sample Courses:**\n" + "\n".join(courses) + "\n• *...and 10 more (C++, Python, Web Designing, Video Editing, Google Workspace Expert).*"
            return {"reply": reply, "source": "Handbook VMDC Kaushal Centre (p. 27)", "quick_actions": ["View All Kaushal Courses", "JMF Scholarship", "Programmes"]}

        # ATKT Rules
        if "atkt" in q or "allowed to keep terms" in q or "keep term" in q:
            atkt_items = self.rules.get("atkt_rules", {}).get("progression", [])
            atkt_str = "\n".join([f"• **{item['to_semester']}**: {item['condition']}" for item in atkt_items])
            reply = f"📖 **Allowed to Keep Terms (ATKT) Rules (Section 3.12):**\n\n{atkt_str}"
            return {"reply": reply, "source": "Handbook Examination Rules (p. 18)", "quick_actions": ["Examination Rules", "College Rules", "Programmes"]}

        # Library Rules
        if any(k in q for k in ["library", "reading room", "library fine", "books issue", "library rules"]):
            reply = f"📚 **College Library Rules:**\n\n" \
                    f"• **Access:** Valid College Identity Card is mandatory for entry.\n" \
                    f"• **Home Issue:** Textbooks issued for a maximum of **7 days**.\n" \
                    f"• **Late Return Fine:** Rs. 1/- per day for the first week, and Rs. 4/- per day in subsequent weeks (holidays are counted). In serious default, up to Rs. 10/- per day.\n" \
                    f"• **Lost/Mutilated Books:** Borrower must replace the book or pay current price + **Rs. 50/- processing charge**.\n" \
                    f"• **Reading Room:** Textbooks and journals issued against I-Cards; strict silence must be maintained. Mobile phones are prohibited."
            return {"reply": reply, "source": "Handbook Library Rules (p. 16, 17)", "quick_actions": ["Book Bank", "College Rules", "Discipline"]}

        # Fee Refund & Admission Cancellation Rules
        if any(k in q for k in ["refund", "cancellation", "cancel admission", "fee refund", "money back", "fees refund"]):
            rules_tbl = self.admissions.get("cancellation_and_refund_rules", {}).get("schedule", [])
            tbl_lines = [f"• **{r['period']}**:\n  ↳ *Deduction:* {r['deduction']} ({r['refund_percentage']})" for r in rules_tbl]
            reply = f"💰 **Fee Refund Rules (University of Mumbai Ordinance 0.2859):**\n\n" \
                    f"Admission cancellation requires an application on the prescribed form with original fee receipt, I-Card, and Library card.\n\n" + \
                    "\n\n".join(tbl_lines) + "\n\n" \
                    f"⚠️ *Note: A penalty of Rs. 100/- is charged for each lost fee receipt.*"
            return {"reply": reply, "source": "Handbook Fee Refund (p. 14)", "quick_actions": ["Admission", "Services", "Scholarships"]}

        # Step 3: Specific Programmes
        # Check B.Sc CS specifically
        if (re.search(r'\b(cs|computer science|bsc cs|b\.sc cs)\b', q)) and not ("bca" in q and "cs" not in q):
            if any(w in q for w in ["subject", "syllabus", "course structure", "semester"]):
                sem1 = ", ".join([f"{s['code']}: {s['name']}" for s in self.course_structure["programmes"]["bsc_cs"]["semesters"]["1"]["subjects"]])
                sem2 = ", ".join([f"{s['code']}: {s['name']}" for s in self.course_structure["programmes"]["bsc_cs"]["semesters"]["2"]["subjects"]])
                reply = f"📘 **B.Sc. Computer Science (B.Sc. CS) Semester Subjects (60 Seats):**\n\n" \
                        f"**Semester I:**\n{sem1}\n\n" \
                        f"**Semester II:**\n{sem2}\n\n" \
                        f"💡 *You can also view the interactive subject matrix under the Course Structure section.*"
                return {"reply": reply, "source": "Handbook Course Structure (B.Sc. CS)", "quick_actions": ["B.Sc IT Subjects", "BCA Subjects", "Eligibility"]}
            
            prog = next((p for p in self.programmes["ug_programmes"] if p["id"] == "bsc_cs"), None)
            reply = f"💻 **{prog['name']}** (Intake: {prog['seats']} Seats)\n\n" \
                    f"**Overview:** {prog['description']}\n\n" \
                    f"**Eligibility:** {prog['eligibility']}\n\n" \
                    f"**Duration:** {prog['duration']}\n" \
                    f"**Key Focus Areas:** {', '.join(prog['specializations'])}."
            return {"reply": reply, "source": "Handbook UG Programmes (p. 2, 7, 24)", "quick_actions": ["B.Sc CS Subjects", "Eligibility", "Documents", "Admission Process"]}

        # Check B.Sc IT specifically (word boundary)
        if re.search(r'\b(it|information technology|bsc it|b\.sc it)\b', q) and not ("msc" in q or "m.sc" in q):
            if any(w in q for w in ["subject", "syllabus", "course structure", "semester"]):
                sem1 = ", ".join([f"{s['code']}: {s['name']}" for s in self.course_structure["programmes"]["bsc_it"]["semesters"]["1"]["subjects"]])
                sem2 = ", ".join([f"{s['code']}: {s['name']}" for s in self.course_structure["programmes"]["bsc_it"]["semesters"]["2"]["subjects"]])
                reply = f"📘 **B.Sc. Information Technology (B.Sc. IT) Semester Subjects (120 Seats):**\n\n" \
                        f"**Semester I:**\n{sem1}\n\n" \
                        f"**Semester II:**\n{sem2}\n\n" \
                        f"💡 *You can view full details in the Course Structure explorer.*"
                return {"reply": reply, "source": "Handbook Course Structure (B.Sc. IT)", "quick_actions": ["B.Sc CS Subjects", "BCA Subjects", "Eligibility"]}

            prog = next((p for p in self.programmes["ug_programmes"] if p["id"] == "bsc_it"), None)
            reply = f"🌐 **{prog['name']}** (Intake: {prog['seats']} Seats)\n\n" \
                    f"**Overview:** {prog['description']}\n\n" \
                    f"**Eligibility:** {prog['eligibility']}\n\n" \
                    f"**Duration:** {prog['duration']}\n" \
                    f"**Specializations:** {', '.join(prog['specializations'])}."
            return {"reply": reply, "source": "Handbook UG Programmes (p. 2, 7, 24)", "quick_actions": ["B.Sc IT Subjects", "B.Sc CS", "Eligibility", "Admission"]}

        # Check General B.Sc (Chemistry, Botany, Zoology)
        if re.search(r'\bb\.?sc\b', q) and not any(k in q for k in ["cs", "it", "computer", "information"]):
            prog = next((p for p in self.programmes["ug_programmes"] if p["id"] == "bsc_general"), None)
            reply = f"🔬 **{prog['name']}** (Intake: {prog['seats']} Seats)\n\n" \
                    f"**Subjects / Specializations:** Chemistry, Botany, Zoology.\n\n" \
                    f"**Eligibility:** {prog['eligibility']}\n\n" \
                    f"**Overview:** {prog['description']}\n" \
                    f"The college has well-equipped laboratories for Botany, Zoology, Physics, and Chemistry."
            return {"reply": reply, "source": "Handbook UG Programmes (p. 2, 24)", "quick_actions": ["B.Sc CS", "B.Sc IT", "Laboratories", "Admission"]}

        # Check BCA
        if re.search(r'\b(bca|b\.c\.a|computer applications?)\b', q):
            if any(w in q for w in ["subject", "syllabus", "semester"]):
                sem1 = ", ".join([f"{s['code']}: {s['name']}" for s in self.course_structure["programmes"]["bca"]["semesters"]["1"]["subjects"]])
                sem2 = ", ".join([f"{s['code']}: {s['name']}" for s in self.course_structure["programmes"]["bca"]["semesters"]["2"]["subjects"]])
                reply = f"💻 **Bachelor of Computer Applications (B.C.A. - AICTE Approved | 60 Seats):**\n\n" \
                        f"**Semester I:**\n{sem1}\n\n" \
                        f"**Semester II:**\n{sem2}\n\n" \
                        f"💡 *BCA includes comprehensive labs in C, C++, Java, Unix, Oracle, Data Structures, and Python across Semesters 1 to 6.*"
                return {"reply": reply, "source": "Handbook AICTE Programmes & Course Structure", "quick_actions": ["B.Sc CS Subjects", "BBA", "Eligibility"]}

            prog = next((p for p in self.programmes["aicte_programmes"] if p["id"] == "bca"), None)
            reply = f"🖥️ **{prog['name']}** ({prog['approval']} - Intake: {prog['seats']} Seats)\n\n" \
                    f"**Overview:** {prog['description']}\n\n" \
                    f"**Eligibility:** {prog['eligibility']}\n\n" \
                    f"**Examination Pattern:** {prog['pattern']}."
            return {"reply": reply, "source": "Handbook AICTE Programmes (p. 2, 8, 24)", "quick_actions": ["BCA Subjects", "BBA", "B.Sc CS", "Admission"]}

        # Check BBA
        if re.search(r'\b(bba|b\.b\.a|business administration)\b', q):
            prog = next((p for p in self.programmes["aicte_programmes"] if p["id"] == "bba"), None)
            reply = f"📊 **{prog['name']}** ({prog['approval']} - Intake: {prog['seats']} Seats)\n\n" \
                    f"**Overview:** {prog['description']}\n\n" \
                    f"**Eligibility:** {prog['eligibility']}\n\n" \
                    f"**Examination Pattern:** {prog['pattern']}\n" \
                    f"Curriculum covers Principles of Management, Human Behavior, Marketing, Financial Management, Startup Ecosystem, and Corporate Governance."
            return {"reply": reply, "source": "Handbook AICTE Programmes (p. 2, 7, 8, 24)", "quick_actions": ["BBA Subjects", "B.Com", "BMS", "Admission"]}

        # Check B.Com / BAF / BMS / BA
        if re.search(r'\b(baf|b\.a\.f|accounting & finance|accounting and finance)\b', q):
            prog = next((p for p in self.programmes["ug_programmes"] if p["id"] == "baf"), None)
            reply = f"📈 **{prog['name']}** (Intake: {prog['seats']} Seats | NEP 2020 60:40 Pattern)\n\n" \
                    f"**Eligibility:** {prog['eligibility']}\n\n" \
                    f"**Description:** {prog['description']}\n" \
                    f"Key Subjects include Financial Accounting, Auditing, IT Fundamentals, Direct/Indirect Tax, and Vocational Accounting Skills."
            return {"reply": reply, "source": "Handbook UG Programmes (p. 4, 24)", "quick_actions": ["BAF Subjects", "B.Com", "BMS", "Fees & Refund"]}

        if re.search(r'\b(bms|b\.m\.s|management studies)\b', q):
            prog = next((p for p in self.programmes["ug_programmes"] if p["id"] == "bms"), None)
            reply = f"👔 **{prog['name']}** (Specializations: Finance, Marketing, HR | Intake: 60 Seats)\n\n" \
                    f"**Eligibility:** {prog['eligibility']}\n\n" \
                    f"**Description:** {prog['description']}."
            return {"reply": reply, "source": "Handbook Programmes Offered (p. 2, 24)", "quick_actions": ["BBA", "B.Com", "Eligibility", "Admission"]}

        if re.search(r'\bb\.?com\b', q) and not any(k in q for k in ["baf", "accounting", "transport", "banking"]):
            prog = next((p for p in self.programmes["ug_programmes"] if p["id"] == "bcom"), None)
            reply = f"💼 **{prog['name']}** (Intake: {prog['seats']} Seats | NEP 2020 60:40 Pattern)\n\n" \
                    f"**Eligibility:** {prog['eligibility']}\n\n" \
                    f"**Description:** {prog['description']}\n\n" \
                    f"Other specialized Commerce degrees available: B.Com (Banking & Insurance), B.Com (Accounting & Finance), B.Com (Financial Management), and B.Com (Transport Management)."
            return {"reply": reply, "source": "Handbook UG Programmes (p. 4, 24)", "quick_actions": ["B.Com Subjects", "BAF", "Eligibility", "Admission"]}

        if re.search(r'\bb\.?a\b', q) and not any(k in q for k in ["bba", "baf", "bca", "bammc"]):
            prog = next((p for p in self.programmes["ug_programmes"] if p["id"] == "ba"), None)
            reply = f"🏛️ **{prog['name']}** (Medium: {prog['medium']} | Intake: {prog['seats']} Seats)\n\n" \
                    f"**Specializations:** History, Economics, English Literature, Geography, Psychology.\n\n" \
                    f"**Eligibility:** {prog['eligibility']}\n\n" \
                    f"Other media-focused BA programmes: B.A. (Film, TV & New Media Production) and B.A. (Multimedia & Mass Communication)."
            return {"reply": reply, "source": "Handbook UG Programmes (p. 4, 24)", "quick_actions": ["BA Subjects", "BAMMC", "Eligibility", "Admission"]}

        # Check PG Programmes
        if any(k in q for k in ["pg", "postgraduate", "master", "m.sc", "msc", "m.com", "mcom", "m.a", "ma history"]):
            if "m.sc it" in q or "msc it" in q or ("msc" in q and "it" in q):
                prog = next((p for p in self.programmes["pg_programmes"] if p["id"] == "msc_it"), None)
                reply = f"🎓 **{prog['name']}** (Intake: {prog['seats']} Seats | 50:50 Pattern)\n\n" \
                        f"**Subjects & Research:** Data Science, Soft Computing, Cloud Computing, Modern Networking, AI & Machine Learning, Blockchain, Cyber Forensics, and Deep Learning.\n\n" \
                        f"**Eligibility:** {prog['eligibility']}."
                return {"reply": reply, "source": "Handbook PG Programmes (p. 11, 24)", "quick_actions": ["M.Sc Chemistry", "M.Com", "B.Sc IT"]}

            if "chemistry" in q or "msc chemistry" in q:
                prog = next((p for p in self.programmes["pg_programmes"] if p["id"] == "msc_chemistry"), None)
                reply = f"🧪 **{prog['name']}** (Intake: {prog['seats']} Seats | 50:50 Pattern)\n\n" \
                        f"**Specializations:** Inorganic, Organic, Analytical, Physical, Synthetic Organic Chemistry, Biogenesis & Green Chemistry, Spectroscopy, and Industrial Training.\n\n" \
                        f"**Eligibility:** {prog['eligibility']}."
                return {"reply": reply, "source": "Handbook PG Programmes (p. 10, 11, 24)", "quick_actions": ["M.Sc IT", "M.Com", "Laboratories"]}

            pg_list = "\n".join([f"• **{p['name']}** ({p['seats']} Seats) - {', '.join(p['specializations'])}" for p in self.programmes["pg_programmes"]])
            reply = f"🎓 **Postgraduate (PG) Programmes Offered at VMDC:**\n\n{pg_list}\n\n" \
                    f"📌 All PG programmes follow the 100 Marks (50:50) examination evaluation pattern affiliated to University of Mumbai."
            return {"reply": reply, "source": "Handbook PG Programmes (p. 2, 24)", "quick_actions": ["M.Sc IT", "M.Com", "M.Sc Chemistry", "M.A History", "UG Programmes"]}

        # Step 4: General Domain Queries
        # Documents Required (make sure not to match bonafide/railway)
        if any(k in q for k in ["documents are required", "documents required", "required documents", "what documents", "papers required", "document checklist"]):
            docs = self.admissions.get("first_year_eligibility", {}).get("documents_required", [])
            doc_str = "\n".join([f"• {d}" for d in docs[:8]])
            reply = f"📋 **Documents Required for First Year Admission:**\n\n{doc_str}\n\n" \
                    f"📌 **Key Deadlines:**\n" \
                    f"• Submit Enrollment Form within 4 days of admission.\n" \
                    f"• Submit Board Certificate + 2 attested copies before **24th December**.\n" \
                    f"• Preserve at least 10 attested photocopies of all marksheets and certificates before submitting originals."
            return {"reply": reply, "source": "Handbook Admission Guidelines (p. 12, 13)", "quick_actions": ["Admission Eligibility", "Scholarship Documents", "Fee Refund Rules"]}

        # Eligibility
        if any(k in q for k in ["eligibility for admission", "eligibility", "eligible", "admission criteria", "who can apply"]):
            reply = f"📝 **General Admission Eligibility (VMDC):**\n\n" \
                    f"• **First Year Degree College:** Passed 12th Std (H.S.C.) conducted by Maharashtra State Board or any recognized equivalent board.\n" \
                    f"• **B.Sc. Computer Science / B.Sc. IT:** Passed 12th Std (H.S.C.) with **Mathematics** as a required subject.\n" \
                    f"• **B.C.A. / B.B.A. (AICTE):** Passed 12th Std in any stream with minimum passing aggregate as per AICTE and University norms.\n" \
                    f"• **B.Com / B.A.F. / B.M.S.:** Passed 12th Std Commerce / Arts / Science.\n" \
                    f"• **Students of Jahnvis Multi Foundation Trust School** are given preference during admission."
            return {"reply": reply, "source": "Handbook Admission Guidelines (p. 12)", "quick_actions": ["Documents Required", "Admission Process", "Fee Refund Rules"]}

        # Admission Process
        if any(k in q for k in ["admission process", "admission guideline", "how to apply", "admission procedure", "admission date", "schedule"]):
            sched = self.admissions.get("general_schedule")
            proc = self.admissions.get("first_year_eligibility", {}).get("procedure")
            reply = f"🏛️ **Admission Guidelines & Procedure:**\n\n" \
                    f"• **Schedule:** {sched}\n" \
                    f"• **Application:** Application must be made on the prescribed printed form available at the college office.\n" \
                    f"• **Fee Payment:** Students granted admission must pay fees on the same day, failing which they will have 'NO CLAIM' to the seat.\n" \
                    f"• **Annual Fee Commitment:** Fees must be paid for the whole year even if the student subsequently leaves or is struck off the roll.\n" \
                    f"• **Verification:** False records or attestation will lead to immediate cancellation and criminal action under IPC sections 470, 471, 474."
            return {"reply": reply, "source": "Handbook Admission Guidelines (p. 12, 24)", "quick_actions": ["Documents Required", "Fee Refund Rules", "Scholarships"]}

        # All Available Courses
        if any(k in q for k in ["courses are available", "courses available", "programmes offered", "programs offered", "degrees offered", "what can i do", "what do you offer"]) or (re.search(r'\b(courses|programmes|programs)\b', q) and not any(k in q for k in ["kaushal", "klic", "skill"])):
            ug_names = [f"• {p['name']}" for p in self.programmes["ug_programmes"]]
            pg_names = [f"• {p['name']}" for p in self.programmes["pg_programmes"]]
            aicte_names = [f"• {p['name']}" for p in self.programmes["aicte_programmes"]]
            reply = f"🎓 **Programmes Offered at Vande Mataram Degree College:**\n\n" \
                    f"**Under-Graduate (UG) Programmes (12):**\n" + "\n".join(ug_names) + "\n\n" \
                    f"**Post-Graduate (PG) Programmes (4):**\n" + "\n".join(pg_names) + "\n\n" \
                    f"**AICTE Approved Programmes (3):**\n" + "\n".join(aicte_names) + "\n\n" \
                    f"🛠️ **VMDC Kaushal Centre:** 20 KLiC skill development courses (120 hrs, Rs. 6000/- each).\n\n" \
                    f"💡 *Ask me about any specific programme for eligibility, syllabus, and seat capacity.*"
            return {"reply": reply, "source": "Handbook Programmes Offered (p. 2, 24)", "quick_actions": ["B.Sc CS", "B.Sc IT", "BCA", "BBA", "B.Com", "Admission Eligibility"]}

        # Attendance Criteria
        if any(k in q for k in ["attendance", "attend", "lecture", "lectures", "75%"]):
            reply = f"📅 **College Attendance Rule:**\n\n" \
                    f"• **Mandatory Requirement:** Under **Ordinance No. O. 6086 of the University of Mumbai**, every student is strictly required to attend **at least 75%** of the total number of Lectures and Practicals conducted during the academic year.\n\n" \
                    f"• **Bunking Policy:** Bunking lectures is a punishable disciplinary offence. Leave of absence requires prior written permission from the class in-charge in case of genuine emergencies."
            return {"reply": reply, "source": "Handbook College Rules (p. 15, Ordinance O.6086)", "quick_actions": ["College Rules", "Discipline", "ATKT Rules"]}

        # Scholarships & Welfare
        if any(k in q for k in ["scholarship", "scholarships", "freeship", "freeships", "jmf scholarship", "financial aid", "student aid", "welfare"]):
            jmf = next((s for s in self.welfare["schemes"] if s["id"] == "jmf_scholarship"), {})
            reply = f"🎓 **Scholarships & Welfare Schemes at VMDC:**\n\n" \
                    f"1. **JMF Scholarship:** {jmf.get('amount')} grant for deserving and economically backward students irrespective of caste/religion.\n\n" \
                    f"2. **Government Freeships/Scholarships:** For SC/ST/OBC/VJNT/SBC/EBC categories (income certificate certified by Tehsildar submitted in June/July).\n\n" \
                    f"3. **Students' Aid Fund & Book Bank:** Provides tuition fee grants, S.T. pass assistance, medical support, and free textbook sets for the full academic year (contribution: Rs. 5/yr).\n\n" \
                    f"4. **Yuva Raksha Insurance Scheme:** Rs. 40/- annual premium provides 100% accidental death/disability coverage and hospitalization support.\n\n" \
                    f"5. **Student Start-Up Scheme:** Seed capital up to **Rs. 5,000/-** provided by the college for student business proposals (approved by Principal)."
            return {"reply": reply, "source": "Handbook Student Welfare (p. 17, 19, 23)", "quick_actions": ["JMF Scholarship", "Book Bank", "Startup Scheme", "Required Documents"]}

        # Extension Services
        if any(k in q for k in ["services are available", "what services", "extension services", "counter", "office services"]) or (re.search(r'\bservices?\b', q) and not any(k in q for k in ["nss", "kaushal", "canteen"])):
            serv_list = [f"• **{s['name']}** ({s['time_minutes']})" for s in self.services.get("services", [])[:10]]
            reply = f"🏢 **College Extension Services (with Turnaround Times):**\n\n" + "\n".join(serv_list) + "\n\n" \
                    f"💡 *The college provides 24 official counter services ranging from immediate clearance to 30 mins.*"
            return {"reply": reply, "source": "Handbook Extension Services (p. 25)", "quick_actions": ["Railway Concession", "Bonafide Certificate", "NOC", "Fees Receipt"]}

        # Committees
        if any(k in q for k in ["committee", "committees", "academic committee", "forum", "forums"]):
            reply = f"👥 **Academic Committees & Forums at VMDC:**\n\n" \
                    f"The college has **over 40 specialized active academic committees**, including:\n\n" \
                    f"• Examination Committee & Results Committee\n" \
                    f"• NAAC Core Committee & IQAC Cell\n" \
                    f"• Attendance & Discipline Committees\n" \
                    f"• Career Guidance, Placement & Internship Committee\n" \
                    f"• Counseling Cell & Women Development Cell\n" \
                    f"• NSS Advisory & NSS Committee\n" \
                    f"• Anti Ragging Committee & Grievance Redressal\n" \
                    f"• VMDC Kaushal Committee & R&D Committee\n" \
                    f"• Happy Club & Cultural Committee."
            return {"reply": reply, "source": "Handbook Academic Committees (p. 21)", "quick_actions": ["NSS", "Counseling Cell", "Student Life"]}

        # Student Life, Activities, Canteen, Gymkhana, Festival
        if any(k in q for k in ["activities are conducted", "activities", "canteen", "gymkhana", "sports", "festival", "prernotsav", "cultural", "student council", "job mela", "placement"]):
            reply = f"🎉 **Student Life & Campus Facilities at VMDC:**\n\n" \
                    f"• **Pure Veg Canteen:** Clean, hygienic, and affordable pure vegetarian canteen for students and staff.\n" \
                    f"• **Gymkhana & Sports:** Outdoor grounds for Cricket, Football, Volleyball, Kabaddi, Kho-Kho; Indoor facility for Table Tennis, Chess, Carrom; and modern gymnasium apparatus.\n" \
                    f"• **PRERNOTSAV:** Intra-collegiate cultural festival organized annually since 2009.\n" \
                    f"• **Job Melas:** Regular campus placement drives, corporate interviews, and soft skill grooming sessions.\n" \
                    f"• **Students' Council:** Merit-based student representation organizing the annual 'Talent Search Parade'."
            return {"reply": reply, "source": "Handbook Student Life (p. 19, 20, 22)", "quick_actions": ["NSS", "Gymkhana", "Canteen", "Committees"]}

        # College Overview, Vision, Mission, Founder
        if any(k in q for k in ["about", "vision", "mission", "founder", "principal", "dr rajkumar kolhe", "overview", "history", "established"]):
            info = self.college_info.get("college", {})
            reply = f"🏛️ **{info.get('name')}**\n\n" \
                    f"• **Established:** Started in 2009 by Hon. Founder President **Dr. Rajkumar Kolhe** under the aegis of **Jahnvis Multi Foundation (JMF)**.\n" \
                    f"• **Location:** Old Dombivli & Kopar area, Dombivli (West), Thane.\n" \
                    f"• **Campus Facilities:** Seven-storied building with Vishwakarma Roof-Top (600 cap), Madhuban Banquet Hall (300 cap), JMF Brahma Rangtalay (1000 cap), and 2 Conference Halls.\n\n" \
                    f"🌟 **Vision:** *\"{info.get('vision')}\"*\n\n" \
                    f"🎯 **Mission:** *\"{info.get('mission')}\"*"
            return {"reply": reply, "source": "Handbook College Overview (p. 2)", "quick_actions": ["Courses Offered", "Admissions", "Campus Facilities"]}

        # Rules, Discipline, Mobile Phones, Smoking
        if any(k in q for k in ["discipline", "rules", "smoking", "tobacco", "mobile phone", "ragging", "id card"]):
            reply = f"⚖️ **College Rules & Code of Conduct:**\n\n" \
                    f"• **ID Card:** Valid College I-Card, Notebook, and Pen are mandatory for entry.\n" \
                    f"• **Attendance:** Minimum 75% attendance under Mumbai University Ordinance O. 6086.\n" \
                    f"• **Mobile Phones:** Strictly prohibited during examinations and in the library (subject to confiscation).\n" \
                    f"• **Strict Prohibitions:** Chewing tobacco, smoking, chewing gum, and loitering in corridors are strictly prohibited.\n" \
                    f"• **Anti-Ragging:** Ragging is a strictly punishable offence under Maharashtra state law."
            return {"reply": reply, "source": "Handbook College Rules (p. 15, 16)", "quick_actions": ["Attendance", "Library Rules", "Fee Refund Rules"]}

        # Fallback: No hallucination
        return {
            "reply": "I don't currently have that specific information in my college knowledge base. You can check directly with the college administrative office or an administrator for official guidance.",
            "source": "Knowledge Base (Unmatched)",
            "quick_actions": ["Courses Available", "Admission Process", "Fee Refund Rules", "Student Services", "Scholarships", "College Rules"]
        }
