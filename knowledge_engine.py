import os
import json
import re
import urllib.request
import urllib.parse
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

    # ─── Language Detection & NLP Typo Normalization ───────────────────────────
    def detect_language(self, text):
        """Detect language: hinglish, hindi, marathi, gujarati, or english."""
        if not text:
            return "en"
        
        # Check Gujarati Unicode range \u0A80-\u0AFF
        if re.search(r'[\u0A80-\u0AFF]', text):
            return "gu"
            
        # Check Devanagari Unicode range \u0900-\u097F
        if re.search(r'[\u0900-\u097F]', text):
            # Differentiate Marathi vs Hindi in Devanagari
            marathi_markers = ["आहे", "कसे", "सांगा", "माहिती", "प्रवेश", "करावे", "नाही", "फी", "अभ्यासक्रम", "शाखा", "कुठे"]
            if any(m in text for m in marathi_markers):
                return "mr"
            return "hi"
            
        t_low = text.lower()
        
        # Romanized Marathi
        roman_marathi = ["sanga", "sang", "kay ahe", "kasa karaycha", "kuthe ahe", "madhe", "kiti", "ahet", "dakhla"]
        if any(w in t_low for w in roman_marathi):
            return "mr"
            
        # Romanized Gujarati
        roman_gujarati = ["kem cho", "su che", "jano", "batao ne", "kya che", "aavshe", "mate"]
        if any(w in t_low for w in roman_gujarati):
            return "gu"
            
        # Hinglish (Romanized Hindi)
        hinglish_words = [
            "mujhe", "mujse", "mujhse", "bata", "batao", "batana", "bataiye", "kya", "hai",
            "kaisa", "kaise", "karna", "kare", "karein", "chahiye", "kitna", "kitni", "konsa",
            "konse", "kaha", "kab", "milega", "padhai", "karo", "hoga", "bolo", "h", "bhai",
            "sir", "madam", "admission", "couse", "cors", "feez", "paise", "kaun", "kiske"
        ]
        tokens = re.findall(r'[a-zA-Z]+', t_low)
        hinglish_count = sum(1 for tok in tokens if tok in hinglish_words)
        
        if hinglish_count >= 1 or any(p in t_low for p in ["ke bare me", "kaise le", "kya hai", "kitna hai", "kab se", "kaha par"]):
            return "hinglish"
            
        return "en"

    def normalize_query(self, query):
        """Fixes phonetic typos and standardizes keywords for robust NLP intent classification."""
        q = query.lower()
        
        # Typo correction table
        replacements = [
            (r'\bcouses?\b|\bcors\b|\bcorse\b|\bkors\b', 'courses'),
            (r'\badmisions?\b|\badmisn\b|\baddmission\b|\badmit\b|\bdakhila\b|\bdakhla\b|\bpravesh\b', 'admission'),
            (r'\bfeez\b|\bfeees\b|\bpaise\b|\bpaisa\b|\bkharcha\b|\bshulk\b', 'fees'),
            (r'\bscolership\b|\bscolarship\b|\bshcolarship\b|\bscholarhips?\b|\bsholarship\b', 'scholarship'),
            (r'\bsubjets?\b|\bsubjetcs\b|\bsylabus\b|\bsylabus\b', 'subjects'),
            (r'\btimig\b|\btimimgs\b|\btym\b|\btyming\b', 'timing'),
            (r'\bdocumnts?\b|\bdocumts?\b|\bpapers?\b|\bdocuments\b', 'documents'),
            (r'\brailwy\b|\bconcesn\b|\bconcesion\b|\btrain pass\b|\bpass\b', 'railway concession'),
            (r'\bbonafid\b|\bbonafied\b|\bcertifcate\b', 'bonafide'),
            (r'\bkaushal\b|\bklic\b|\bskill center\b', 'kaushal'),
            (r'\bprinsipal\b|\bprinciple\b', 'principal'),
            (r'\batkt\b|\bkt\b|\bbacklog\b|\bbacklogs\b', 'atkt')
        ]
        
        for pattern, replacement in replacements:
            q = re.sub(pattern, replacement, q)
            
        return q

    # ─── LLM Integration (Google Gemini with Fallback) ────────────────────────
    def _call_gemini_llm(self, user_message, detected_lang, context_summary):
        """Optionally uses Gemini LLM if GEMINI_API_KEY is configured."""
        config_path = os.path.join(os.path.dirname(__file__), "admin_config.json")
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    api_key = cfg.get("gemini_api_key")
            except Exception:
                pass

        if not api_key:
            return None

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            system_prompt = (
                "You are College Connect AI, the official assistant for JMF's Vande Mataram Degree College, Dombivli (affiliated to University of Mumbai). "
                f"Ground your answer STRICTLY in the provided College Knowledge Base context. "
                f"IMPORTANT: The user asked in '{detected_lang}' language. You MUST respond in the EXACT SAME LANGUAGE/STYLE "
                f"(e.g. if Hinglish, reply in friendly Hinglish; if Marathi, reply in clean Marathi; if Hindi, reply in Hindi; if Gujarati, reply in Gujarati; if English, reply in English). "
                "Keep formatting structured, professional, concise, with helpful markdown bullet points and emojis."
            )
            
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"System Context:\n{system_prompt}\n\nCollege Knowledge Base:\n{context_summary}\n\nUser Question:\n{user_message}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 600
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
        except Exception as e:
            print(f"Gemini LLM Call skipped/failed: {e}")
            return None

    # ─── Global Search ────────────────────────────────────────────────────────
    def search_all(self, query):
        if not query or len(query.strip()) < 2:
            return []
        
        q = self.normalize_query(query)
        tokens = re.findall(r'\w+', q)
        results = []

        def match_score(text):
            if not text: return 0
            t = str(text).lower()
            if q in t: return 10
            score = 0
            for token in tokens:
                if len(token) > 2 and token in t: score += 2
            return score

        def generate_snippet(text):
            text_str = str(text).replace('\n', ' ')
            t = text_str.lower()
            idx = t.find(q)
            if idx == -1:
                for token in tokens:
                    if len(token) > 2:
                        idx = t.find(token)
                        if idx != -1: break
            if idx == -1: return text_str[:140] + "..."
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
                    if current_category in ["college_data", "college_info"]: url = "/"
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

        seen = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x["score"], reverse=True):
            if r["snippet"] not in seen:
                seen.add(r["snippet"])
                unique_results.append(r)

        return unique_results

    # ─── Main Multilingual NLP Query Answering ────────────────────────────────
    def answer_query(self, user_message):
        """Processes multilingual queries in Hinglish, Hindi, Marathi, Gujarati, and English."""
        if not user_message or not user_message.strip():
            return {
                "reply": "Please ask a question regarding Vande Mataram Degree College programmes, admissions, attendance, fees, scholarships, or services.",
                "source": "System",
                "quick_actions": ["Courses", "Admission", "Eligibility", "Scholarships", "Services"]
            }

        raw_query = user_message.strip()
        lang = self.detect_language(raw_query)
        q = self.normalize_query(raw_query)
        self.reload_all()

        # ─── Conversational / Greetings / Creator Small Talk ──────────────────
        # 1. Creator / Developer Query ("Kisne banaya hai", "Who made you", "Aditya Singh")
        creator_patterns = [
            r'\b(kisne banaya|kisne banaya hai|who made you|who created you|who is your creator|who developed you|who is the developer|developer|creator|aditya|aditya singh|kone banavyu|koni banavla|kon banavla|banaya kisne|develop kisne kiya)\b'
        ]
        if any(re.search(pat, q) for pat in creator_patterns) or ("aditya" in q) or ("kisne" in q and "banaya" in q):
            if lang == "hinglish":
                reply = "👨‍💻 **Creator Info:**\n\nMujhe **Aditya Singh** ne banaya hai, jo isi **Vande Mataram Degree College** ke student hain! 🎓\n\nMain college ka official AI Assistant hu jo aapko admission, courses, syllabus, fees, scholarships, rules aur counter services ki bilkul sahi jankari deta hu. Aap mujhse college ke baare me kuch bhi puch sakte hain!"
            elif lang == "mr":
                reply = "👨‍💻 **निर्माता माहिती:**\n\nमला **आदित्य सिंग** यांनी विकसित केले आहे, जे याच **वंदे मातरम डिग्री कॉलेज** चे विद्यार्थी आहेत! 🎓\n\nमी या महाविद्यालयाचा अधिकृत AI सहाय्यक आहे आणि तुम्हाला प्रवेश, अभ्यासक्रम, फी, शिष्यवृत्ती आणि सेवांबद्दल अचूक माहिती देतो."
            elif lang == "hi":
                reply = "👨‍💻 **डेवलपर की जानकारी:**\n\nमुझे **आदित्य सिंह** ने बनाया है, जो इसी **वंदे मातरम डिग्री कॉलेज** के छात्र हैं! 🎓\n\nमैं इस कॉलेज का आधिकारिक AI असिस्टेंट हूँ जो आपको प्रवेश, कोर्सेस, फीस, छात्रवृत्ति और अन्य सुविधाओं की पूरी जानकारी प्रदान करता हूँ।"
            elif lang == "gu":
                reply = "👨‍💻 **ડેવલપર માહિતી:**\n\nમને **આદિત્ય સિંહ** દ્વારા બનાવવામાં આવ્યો છે, જે આ જ **વંદે માતરમ ડિગ્રી કોલેજ** ના વિદ્યાર્થી છે! 🎓\n\nહું કોલેજનો સત્તાવાર AI આસિસ્ટન્ટ છું જે તમને એડમિશન, કોર્સ, ફી અને સ્કોલરશિપની માહિતી પૂરી પાડું છું."
            else:
                reply = "👨‍💻 **Developer & Creator:**\n\nI was created and developed by **Aditya Singh**, a student right here at **Vande Mataram Degree College**! 🎓\n\nI serve as the official College AI Assistant to help students, parents, and visitors with admissions, course structures, syllabus, scholarships, fees, and campus services."
            return {
                "reply": reply,
                "source": "Developer (Aditya Singh - VMDC Student)",
                "quick_actions": ["Courses Offered", "Admissions", "Student Services", "Scholarships"]
            }

        # 2. Greetings & Salutations ("Hi", "Hello", "Hey", "Namaste", "Kem Cho", "Kasa Kay")
        greeting_words = ["hi", "hello", "hey", "hii", "heyy", "hlo", "namaste", "namaskar", "kem cho", "kasa kay", "good morning", "good evening", "good afternoon", "gm", "gn", "sup", "yo", "pranam"]
        tokens_list = re.findall(r'\w+', q)
        is_greeting = (len(tokens_list) <= 3 and any(w in greeting_words for w in tokens_list)) or q in greeting_words or any(q.startswith(g) for g in ["hi ", "hello ", "namaste ", "hey "])
        
        if is_greeting and not any(k in q for k in ["course", "admission", "fee", "scholarship", "bonafide", "railway", "rule"]):
            if lang == "hinglish":
                reply = "👋 **Namaste! Welcome to College Connect AI!**\n\nMain **Vande Mataram Degree College** ka official AI Assistant hu. Main aapki kya madad kar sakta hu?\n\n• Courses & Syllabus 📚\n• Admissions & Documents 📝\n• Fees & Scholarships 🎓\n• Railway Concession & Bonafide 🚆\n• College Timings & Rules ⏰"
            elif lang == "mr":
                reply = "👋 **नमस्कार! कॉलेज कनेक्ट AI मध्ये आपले स्वागत आहे!**\n\nमी **वंदे मातरम डिग्री कॉलेज** चा अधिकृत AI सहाय्यक आहे. मी तुम्हाला कशी मदत करू शकतो?\n\n• अभ्यासक्रम आणि विषय 📚\n• प्रवेश प्रक्रिया आणि पात्रता 📝\n• फी आणि शिष्यवृत्ती 🎓\n• रेल्वे सवलत आणि बोनाफाईड 🚆\n• महाविद्यालयाचे नियम आणि वेळ ⏰"
            elif lang == "hi":
                reply = "👋 **नमस्ते! कॉलेज कनेक्ट AI में आपका स्वागत है!**\n\nमैं **वंदे मातरम डिग्री कॉलेज** का आधिकारिक AI असिस्टेंट हूँ। मैं आपकी क्या मदद कर सकता हूँ?\n\n• कोर्सेस और सिलेबस 📚\n• प्रवेश और आवश्यक दस्तावेज 📝\n• फीस और छात्रवृत्ति 🎓\n• रेलवे रियायत और बोनाफाइड 🚆\n• कॉलेज के नियम और समय ⏰"
            elif lang == "gu":
                reply = "👋 **નમસ્તે! કોલેજ કનેક્ટ AI માં આપનું સ્વાગત છે!**\n\nહું **વંદે માતરમ ડિગ્રી કોલેજ** નો સત્તાવાર AI આસિસ્ટન્ટ છું. હું તમને કેવી રીતે મદદ કરી શકું?\n\n• કોર્સ અને સિલેબસ 📚\n• એડમિશન અને પાત્રતા 📝\n• ફી અને સ્કોલરશિપ 🎓\n• રેલ્વે કન્સેશન 🚆"
            else:
                reply = "👋 **Hello! Welcome to College Connect AI!**\n\nI am the official information assistant for **Vande Mataram Degree College** (Affiliated to University of Mumbai). How can I assist you today?\n\n• Degree Programmes & Course Structure 📚\n• Admissions & Eligibility Criteria 📝\n• Scholarships, Grants & Welfare 🎓\n• Railway Concession & Bonafide Certificates 🚆\n• College Rules, Attendance & Facilities 🏛️"
            return {
                "reply": reply,
                "source": "College Assistant",
                "quick_actions": ["Courses Available", "Admission Eligibility", "Scholarships", "Railway Concession"]
            }

        # 3. How are you / Kya haal hai
        if any(k in q for k in ["how are you", "kaise ho", "kasa ahes", "kasa kay", "kem cho", "kya haal hai", "kya chal raha hai"]):
            if lang == "hinglish":
                reply = "Main bilkul badhiya hu! 😊 Vande Mataram Degree College ke admissions, courses ya services ke baare me aap kya janna chahte hain?"
            elif lang == "mr":
                reply = "मी एकदम मजेत आहे! 😊 वंदे मातरम डिग्री कॉलेजच्या प्रवेश, अभ्यासक्रम किंवा सेवांबद्दल तुम्हाला काय जाणून घ्यायचे आहे?"
            elif lang == "hi":
                reply = "मैं बिल्कुल ठीक हूँ! 😊 वंदे मातरम डिग्री कॉलेज के प्रवेश, कोर्सेस या सेवाओं के बारे में आप क्या जानना चाहते हैं?"
            else:
                reply = "I'm doing great, thank you for asking! 😊 How can I help you with Vande Mataram Degree College information today?"
            return {
                "reply": reply,
                "source": "College Assistant",
                "quick_actions": ["Courses", "Admissions", "Scholarships", "Services"]
            }

        # 4. Thank you / Gratitude
        if any(k in q for k in ["thank you", "thanks", "dhanyawad", "shukriya", "aabhar", "thanks a lot", "bohot shukriya"]):
            if lang == "hinglish":
                reply = "Aapka swagat hai! 🙌 Agar aapko college se related koi aur jankari chahiye ho toh bejhijhak puchiye."
            elif lang == "mr":
                reply = "आपले स्वागत आहे! 🙌 कॉलेज संदर्भात इतर काही माहिती हवी असल्यास नक्की विचारा."
            elif lang == "hi":
                reply = "आपका स्वागत है! 🙌 कॉलेज से संबंधित किसी भी अन्य जानकारी के लिए कभी भी पूछ सकते हैं।"
            else:
                reply = "You're most welcome! 🙌 Let me know if you have any more questions about Vande Mataram Degree College."
            return {
                "reply": reply,
                "source": "College Assistant",
                "quick_actions": ["Courses", "Admissions", "Services"]
            }

        # 5. Step 1: Active Notices / Updates check
        is_update_query = any(k in q for k in ["portal", "result", "notice", "announcement", "update", "latest news", "result portal"])
        if is_update_query:
            for update in self.get_latest_updates():
                title = update.get("title", "").lower()
                content = update.get("content", "").lower()
                if ("result" in q and ("result" in title or "result" in content)) or \
                   ("portal" in q and ("portal" in title or "portal" in content)) or \
                   any(word in q for word in ["mahadbt", "xyz", "notice", "announcement"] if word in (title + content)):
                    
                    if lang == "hinglish":
                        reply = f"📢 **Latest Update: {update.get('title')}** ({update.get('category')} - {update.get('date_added')})\n\n{update.get('content')}"
                    elif lang == "mr":
                        reply = f"📢 **नवीन सूचना: {update.get('title')}** ({update.get('category')} - {update.get('date_added')})\n\n{update.get('content')}"
                    elif lang == "hi":
                        reply = f"📢 **नवीनतम सूचना: {update.get('title')}** ({update.get('category')} - {update.get('date_added')})\n\n{update.get('content')}"
                    elif lang == "gu":
                        reply = f"📢 **તાજેતરની સૂચના: {update.get('title')}** ({update.get('category')} - {update.get('date_added')})\n\n{update.get('content')}"
                    else:
                        reply = f"📢 **{update.get('title')}** ({update.get('category')} - {update.get('date_added')})\n\n{update.get('content')}"
                        
                    if update.get("url"):
                        reply += f"\n\n🔗 [Official Portal Link]({update.get('url')})"
                    return {
                        "reply": reply,
                        "source": f"Latest Update ({update.get('source', 'College Office')})",
                        "quick_actions": ["More Updates", "Admissions", "Contact Office"]
                    }

        # Step 2: Specific Services & Operations
        # Bonafide Certificate
        if "bonafide" in q:
            bon = next((s for s in self.services["services"] if s["id"] == "bonafide_certificate"), {})
            if lang == "hinglish":
                reply = f"📄 **Bonafide Certificate Procedure (Time: {bon.get('time_minutes', '05 mins')}):**\n\n" \
                        f"• **Regular Students:** Ek application form submit karein jisme Full Name, Address, Class, Roll No., DOB aur Academic Year (e.g. 2024-25) likha ho.\n" \
                        f"• **Repeater Students:** Application ke saath last year ki mark sheet ki attested copy lagegi.\n\n" \
                        f"Office counter par working hours me form jama karein."
            elif lang == "mr":
                reply = f"📄 **बोनाफाईड प्रमाणपत्र प्रक्रिया (वेळ: {bon.get('time_minutes', '०५ मिनिटे')}):**\n\n" \
                        f"• **नियमित विद्यार्थी:** नाव, पत्ता, वर्ग, रोल नंबर, जन्मतारीख आणि शैक्षणिक वर्ष नमूद केलेला अर्ज सादर करा.\n" \
                        f"• **रिपीटर विद्यार्थी:** अर्ज + मागील वर्षाच्या गुणपत्रिकेची साक्षांकित प्रत.\n\n" \
                        f"महाविद्यालयाच्या कार्यालयीन वेळेत काउंटरवर अर्ज जमा करा."
            elif lang == "hi":
                reply = f"📄 **बोनाफाइड सर्टिफिकेट प्रक्रिया (समय: {bon.get('time_minutes', '05 मिनट')}):**\n\n" \
                        f"• **नियमित छात्र:** आवेदन पत्र में नाम, पता, कक्षा, रोल नंबर, जन्म तिथि और शैक्षणिक वर्ष भरकर जमा करें।\n" \
                        f"• **रिपीटर छात्र:** आवेदन के साथ पिछले वर्ष की अंकतालिका की सत्यापित प्रति संलग्न करें।\n\n" \
                        f"कॉलेज कार्यालय के काउंटर पर कार्य समय के दौरान संपर्क करें।"
            elif lang == "gu":
                reply = f"📄 **બોનાફાઇડ સર્ટિફિકેટ પ્રક્રિયા (સમય: {bon.get('time_minutes', '05 મિનિટ')}):**\n\n" \
                        f"• **નિયમિત વિદ્યાર્થીઓ:** નામ, સરનામું, વર્ગ, રોલ નંબર, જન્મ તારીખ અને શૈક્ષણિક વર્ષ સાથેની અરજી સબમિટ કરો.\n" \
                        f"• **રિપીટર વિદ્યાર્થીઓ:** અરજી સાથે છેલ્લા વર્ષની માર્કશીટની ઝેરોક્ષ.\n\n" \
                        f"ઓફિસ કાઉન્ટર પર કામકાજના સમય દરમિયાન સબમિટ કરો."
            else:
                reply = f"📄 **Bonafide Certificate Procedure (Turnaround: {bon.get('time_minutes', '05 mins')}):**\n\n" \
                        f"• **Regular Students:** Submit an application stating Student's Full Name, Address, Class, Roll Number, Date of Birth, and Academic Year.\n" \
                        f"• **Repeater Students:** Application + Attested photocopy of last year's mark sheet.\n\n" \
                        f"Submit at the college administrative office counter during working hours."
            return {"reply": reply, "source": "Handbook Extension Services (p. 15, 25)", "quick_actions": ["Railway Concession", "NOC", "Student Services"]}

        # Railway Concession
        if any(k in q for k in ["railway", "concession", "train", "pass", "season ticket", "kopar"]):
            rail = next((s for s in self.services["services"] if s["id"] == "railway_concession"), {})
            if lang == "hinglish":
                reply = f"🚆 **Railway Concession Form & Process (Time: {rail.get('time_minutes', '05 mins')}):**\n\n" \
                        f"• **Eligibility:** 25 saal se kam umar ke bonafide degree college students.\n" \
                        f"• **Route:** Residence station se **Kopar Station** tak concession pass milta hai.\n" \
                        f"• **Required Documents:** Prescribed form + Ration card ya valid address proof ki attested copy.\n" \
                        f"• **Submission Time:** Recess ke dauran aur lectures ke baad office counter par."
            elif lang == "mr":
                reply = f"🚆 **रेल्वे सवलत (Railway Concession) प्रक्रिया (वेळ: ०५ मिनिटे):**\n\n" \
                        f"• **पात्रता:** २५ वर्षांखालील महाविद्यालयाचे नियमित विद्यार्थी.\n" \
                        f"• **मार्ग:** घराचे जवळचे स्टेशन ते **कोपर स्टेशन** दरम्यान पास सवलत मिळते.\n" \
                        f"• **आवश्यक कागदपत्रे:** विहित अर्ज + रेशन कार्ड किंवा रहिवासी पुराव्याची साक्षांकित प्रत.\n" \
                        f"• **वेळ:** मधल्या सुट्टीत किंवा लेक्चर्स संपल्यानंतर कार्यालयीन काउंटरवर अर्ज स्वीकारले जातात."
            elif lang == "hi":
                reply = f"🚆 **रेलवे कंसेशन प्रक्रिया (समय: 05 मिनट):**\n\n" \
                        f"• **पात्रता:** 25 वर्ष से कम आयु के नियमित छात्र।\n" \
                        f"• **रूट:** निवास स्थान के निकटतम स्टेशन से **कोपर स्टेशन** तक रियायत मिलती है।\n" \
                        f"• **दस्तावेज:** निर्धारित आवेदन पत्र + राशन कार्ड या निवास प्रमाण पत्र की सत्यापित प्रति।\n" \
                        f"• **जमा करने का समय:** लंच ब्रेक और व्याख्यान समाप्त होने के बाद।"
            elif lang == "gu":
                reply = f"🚆 **રેલ્વે કન્સેશન પ્રક્રિયા (સમય: 05 મિનિટ):**\n\n" \
                        f"• **પાત્રતા:** 25 વર્ષથી ઓછી ઉંમરના નિયમિત વિદ્યાર્થીઓ.\n" \
                        f"• **રૂટ:** રહેઠાણના સ્ટેશનથી **કોપર સ્ટેશન** સુધી કન્સેશન મળે છે.\n" \
                        f"• **જરૂરી દસ્તાવેજો:** નિયત અરજી ફોર્મ + રેશનકાર્ડ અથવા સરનામાનો પુરાવો."
            else:
                reply = f"🚆 **Railway Concession Procedure (Turnaround: {rail.get('time_minutes', '05 mins')}):**\n\n" \
                        f"• **Eligibility:** Bonafide students of the college below **25 years of age**.\n" \
                        f"• **Season Tickets:** Granted between the student's residence station and **Kopar station**.\n" \
                        f"• **Documents Required:** Prescribed application form + Attested photocopy of Ration Card or residence proof.\n" \
                        f"• **Timing:** Applications accepted between recess and after lectures on working days."
            return {"reply": reply, "source": "Handbook Extension Services & Rules (p. 15, 25)", "quick_actions": ["Bonafide Certificate", "Student Services", "Rules"]}

        # Specific Degree: B.Sc Computer Science
        if re.search(r'\b(cs|computer science|bsc cs|b\.sc cs)\b', q) and not ("bca" in q and "cs" not in q):
            prog = next((p for p in self.programmes["ug_programmes"] if p["id"] == "bsc_cs"), None)
            sem1 = ", ".join([f"{s['code']}: {s['name']}" for s in self.course_structure["programmes"]["bsc_cs"]["semesters"]["1"]["subjects"][:5]])
            if lang == "hinglish":
                reply = f"💻 **B.Sc. Computer Science (B.Sc. CS)** (Intake: 60 Seats)\n\n" \
                        f"• **Eligibility:** 12th Std (HSC) Science pass with **Mathematics** compulsory subject.\n" \
                        f"• **Duration:** 3 Years (6 Semesters) affiliated to Mumbai University.\n" \
                        f"• **Sem 1 Core Papers:** {sem1}...\n" \
                        f"• **Careers:** Software Engineer, Web Developer, Cyber Security Analyst, Cloud Consultant."
            elif lang == "mr":
                reply = f"💻 **बी.एस्सी. कॉम्प्युटर सायन्स (B.Sc. CS)** (प्रवेश क्षमता: ६० जागा)\n\n" \
                        f"• **पात्रता:** १२ वी (HSC) विज्ञान उत्तीर्ण सह **गणित (Mathematics)** विषय अनिवार्य.\n" \
                        f"• **कालावधी:** ३ वर्षे (६ सेमिस्टर्स) - मुंबई विद्यापीठाशी संलग्न.\n" \
                        f"• **प्रमुख विषय:** ओपन सोर्स तंत्रज्ञान, वेब तंत्रज्ञान, सायबर सुरक्षा, पायथॉन आणि डेटा स्ट्रक्चर्स."
            elif lang == "hi":
                reply = f"💻 **बी.एससी. कंप्यूटर साइंस (B.Sc. CS)** (कुल सीटें: 60)\n\n" \
                        f"• **पात्रता:** 12वीं साइंस उत्तीर्ण जिसमें **गणित (Mathematics)** अनिवार्य विषय हो।\n" \
                        f"• **अवधि:** 3 वर्ष (6 सेमेस्टर) - मुंबई विश्वविद्यालय से संबद्ध।\n" \
                        f"• **करियर विकल्प:** सॉफ्टवेयर डेवलपर, डेटा एनालिस्ट, वेब डेवलपर, साइबर सिक्योरिटी एक्सपर्ट।"
            elif lang == "gu":
                reply = f"💻 **બી.એસસી. કમ્પ્યુટર સાયન્સ (B.Sc. CS)** (કુલ સીટો: 60)\n\n" \
                        f"• **પાત્રતા:** 12મું સાયન્સ પાસ સાથે **ગણિત (Maths)** વિષય ફરજિયાત.\n" \
                        f"• **સમયગાળો:** 3 વર્ષ (6 સેમેસ્ટર) - મુંબઈ યુનિવર્સિટી સંલગ્ન.\n" \
                        f"• **કારકિર્દી:** સોફ્ટવેર એન્જિનિયર, વેબ ડેવલપર, ડેટા સાયન્ટિસ્ટ."
            else:
                reply = f"💻 **{prog['name']}** (Intake: {prog['seats']} Seats)\n\n" \
                        f"**Overview:** {prog['description']}\n\n" \
                        f"**Eligibility:** {prog['eligibility']}\n\n" \
                        f"**Duration:** {prog['duration']}\n" \
                        f"**Key Focus Areas:** {', '.join(prog['specializations'])}."
            return {"reply": reply, "source": "Handbook UG Programmes (p. 2, 7, 24)", "quick_actions": ["B.Sc CS Subjects", "B.Sc IT", "Admission Process", "Eligibility"]}

        # Specific Degree: B.Sc IT
        if re.search(r'\b(it|information technology|bsc it|b\.sc it)\b', q) and not ("msc" in q or "m.sc" in q):
            prog = next((p for p in self.programmes["ug_programmes"] if p["id"] == "bsc_it"), None)
            if lang == "hinglish":
                reply = f"🌐 **B.Sc. Information Technology (B.Sc. IT)** (Intake: 120 Seats)\n\n" \
                        f"• **Eligibility:** 12th Std (HSC) pass with **Mathematics** compulsory.\n" \
                        f"• **Duration:** 3 Years (6 Semesters).\n" \
                        f"• **Key Topics:** Networking, Database Management, Web Designing, Cloud Computing, Data Science.\n" \
                        f"• **Seats:** 120 Seats available in VMDC."
            elif lang == "mr":
                reply = f"🌐 **बी.एस्सी. इन्फॉर्मेशन टेक्नॉलॉजी (B.Sc. IT)** (प्रवेश क्षमता: १२० जागा)\n\n" \
                        f"• **पात्रता:** १२ वी (HSC) उत्तीर्ण सह **गणित (Mathematics)** विषय आवश्यक.\n" \
                        f"• **कालावधी:** ३ वर्षे (६ सेमिस्टर्स).\n" \
                        f"• **प्रमुख विषय:** नेटवर्किंग, क्लाउड कम्प्युटिंग, डेटा सायन्स, वेब प्रोग्रामिंग आणि डेटाबेस."
            elif lang == "hi":
                reply = f"🌐 **बी.एससी. इंफॉर्मेशन टेक्नोलॉजी (B.Sc. IT)** (कुल सीटें: 120)\n\n" \
                        f"• **पात्रता:** 12वीं उत्तीर्ण जिसमें **गणित (Mathematics)** विषय शामिल हो।\n" \
                        f"• **अवधि:** 3 वर्ष (6 सेमेस्टर)।\n" \
                        f"• **करियर विकल्प:** नेटवर्क इंजीनियर, सिस्टम एडमिनिस्ट्रेटर, क्लाउड आर्किटेक्ट, आईटी कंसल्टेंट।"
            elif lang == "gu":
                reply = f"🌐 **બી.એસસી. ઇન્ફોર્મેશન ટેકનોલોજી (B.Sc. IT)** (કુલ સીટો: 120)\n\n" \
                        f"• **પાત્રતા:** 12મું પાસ સાથે **ગણિત (Maths)** વિષય હોવો જરૂરી છે.\n" \
                        f"• **સમયગાળો:** 3 વર્ષ.\n" \
                        f"• **કારકિર્દી:** નેટવર્ક એન્જિનિયર, ક્લાઉડ એક્સપર્ટ, આઇટી પ્રોફેશનલ."
            else:
                reply = f"🌐 **{prog['name']}** (Intake: {prog['seats']} Seats)\n\n" \
                        f"**Overview:** {prog['description']}\n\n" \
                        f"**Eligibility:** {prog['eligibility']}\n\n" \
                        f"**Duration:** {prog['duration']}\n" \
                        f"**Specializations:** {', '.join(prog['specializations'])}."
            return {"reply": reply, "source": "Handbook UG Programmes (p. 2, 7, 24)", "quick_actions": ["B.Sc IT Subjects", "B.Sc CS", "Eligibility", "Admission"]}

        # Specific Degree: BCA / BBA (AICTE)
        if re.search(r'\b(bca|b\.c\.a|computer applications?)\b', q):
            prog = next((p for p in self.programmes["aicte_programmes"] if p["id"] == "bca"), None)
            if lang == "hinglish":
                reply = f"💻 **Bachelor of Computer Applications (B.C.A. - AICTE Approved)** (60 Seats)\n\n" \
                        f"• **Eligibility:** 12th Std (HSC) pass in Any Stream (Science / Commerce / Arts).\n" \
                        f"• **Key Skills:** C, C++, Java, Python, Web Design, DBMS, Cloud Computing, Business Intelligence.\n" \
                        f"• **Exam Pattern:** 100 Marks (75:25 Pattern)."
            elif lang == "mr":
                reply = f"💻 **बॅचलर ऑफ कॉम्प्युटर ॲप्लिकेशन्स (B.C.A. - AICTE मान्यताप्राप्त)** (६० जागा)\n\n" \
                        f"• **पात्रता:** १२ वी (कोणतीही शाखा - विज्ञान / वाणिज्य / कला) उत्तीर्ण.\n" \
                        f"• **अभ्यासक्रम:** सी, सी++, जावा, पायथॉन, डेटाबेस, क्लाउड कम्प्युटिंग आणि वेब डिझायनिंग."
            elif lang == "hi":
                reply = f"💻 **बैचलर ऑफ कंप्यूटर एप्लीकेशन (B.C.A. - AICTE स्वीकृत)** (60 सीटें)\n\n" \
                        f"• **पात्रता:** किसी भी संकाय (साइंस / कॉमर्स / आर्ट्स) से 12वीं उत्तीर्ण।\n" \
                        f"• **मुख्य विषय:** सी, सी++, जावा, पायथन, डेटाबेस, वेब डेवलपमेंट और सॉफ्टवेयर इंजीनियरिंग।"
            elif lang == "gu":
                reply = f"💻 **બેચલર ઓફ કમ્પ્યુટર એપ્લિકેશન્સ (B.C.A. - AICTE માન્ય)** (60 સીટો)\n\n" \
                        f"• **પાત્રતા:** કોઈપણ પ્રવાહ (સાયન્સ / કોમર્સ / આર્ટસ) માં 12મું પાસ.\n" \
                        f"• **વિષયો:** પ્રોગ્રામિંગ (C, C++, Java, Python), ડેટાબેઝ, વેબ ડેવલપમેન્ટ."
            else:
                reply = f"🖥️ **{prog['name']}** ({prog['approval']} - Intake: {prog['seats']} Seats)\n\n" \
                        f"**Overview:** {prog['description']}\n\n" \
                        f"**Eligibility:** {prog['eligibility']}\n\n" \
                        f"**Examination Pattern:** {prog['pattern']}."
            return {"reply": reply, "source": "Handbook AICTE Programmes (p. 2, 8, 24)", "quick_actions": ["BCA Subjects", "BBA", "B.Sc CS", "Admission"]}

        # General Available Courses / Programmes Query (Matches "mujse couse ke bare me bata", "courses", etc.)
        if any(k in q for k in ["courses", "programmes", "programs", "degrees", "degree", "branch", "offer", "padhai", "shakha"]) or \
           ("bare me bata" in q and "course" in q) or (lang in ["mr", "hi", "gu"] and any(k in q for k in ["कोर्स", "अभ्यासक्रम", "शाखा", "કોર્સ"])):
            
            if lang == "hinglish":
                reply = f"🎓 **Vande Mataram Degree College ke Available Courses & Programmes:**\n\n" \
                        f"College me University of Mumbai se affiliated total **12 UG**, **4 PG** aur AICTE approved degree programmes offer kiye jaate hain:\n\n" \
                        f"**1. Under-Graduate (UG) Degrees (3 Years):**\n" \
                        f"• **B.Sc. Computer Science (B.Sc. CS)** — 60 Seats\n" \
                        f"• **B.Sc. Information Technology (B.Sc. IT)** — 120 Seats\n" \
                        f"• **B.C.A.** (Computer Applications - AICTE) — 60 Seats\n" \
                        f"• **B.B.A.** (Business Administration - AICTE) — 60 Seats\n" \
                        f"• **B.Com** (General, BAF, BBI, BFM, BTM) — 60-120 Seats\n" \
                        f"• **B.A.** (History, Economics, Psychology, Literature, Film & TV Production)\n" \
                        f"• **B.Sc.** (Chemistry, Botany, Zoology)\n\n" \
                        f"**2. Post-Graduate (PG) Degrees (2 Years):**\n" \
                        f"• M.Sc. IT, M.Sc. Chemistry, M.Com (Advanced Accountancy), M.A. History\n\n" \
                        f"🛠️ **Kaushal Centre:** 20 Job-Oriented KLiC Certification Courses (Rs. 6000/-, 120 Hrs).\n\n" \
                        f"👉 *Aap kisi bhi specific course ki eligibility, subjects ya fees ke bare me puch sakte hain!*"
            elif lang == "mr":
                reply = f"🎓 **वंदे मातरम डिग्री कॉलेजमधील कोर्सेस आणि अभ्यासक्रम:**\n\n" \
                        f"महाविद्यालयात मुंबई विद्यापीठाशी संलग्न पदवी (UG), पदव्युत्तर (PG) आणि AICTE मान्यताप्राप्त कोर्सेस उपलब्ध आहेत:\n\n" \
                        f"**१. पदवी (UG) अभ्यासक्रम (३ वर्षे):**\n" \
                        f"• बी.एस्सी. कॉम्प्युटर सायन्स (B.Sc. CS) - ६० जागा\n" \
                        f"• बी.एस्सी. इन्फॉर्मेशन टेक्नॉलॉजी (B.Sc. IT) - १२० जागा\n" \
                        f"• बी.सी.ए. (B.C.A. - AICTE) - ६० जागा\n" \
                        f"• बी.बी.ए. (B.B.A. - AICTE) - ६० जागा\n" \
                        f"• बी.कॉम (B.Com / BAF / BBI / BFM / BTM)\n" \
                        f"• बी.ए. (B.A. / BAMMC / Film & TV Production)\n" \
                        f"• बी.एस्सी. जनरल (रसायनशास्त्र, वनस्पतीशास्त्र, प्राणीशास्त्र)\n\n" \
                        f"**२. पदव्युत्तर (PG) अभ्यासक्रम (२ वर्षे):**\n" \
                        f"• एम.एस्सी. आयटी, एम.एस्सी. केमिस्ट्री, एम.कॉम, एम.ए. इतिहास\n\n" \
                        f"🛠️ **कौशल्य केंद्र:** २० नोकरीभिमुख KLiC प्रमाणपत्र कोर्सेस."
            elif lang == "hi":
                reply = f"🎓 **वंदे मातरम डिग्री कॉलेज में उपलब्ध कोर्सेस:**\n\n" \
                        f"कॉलेज में मुंबई विश्वविद्यालय से संबद्ध अंडरग्रेजुएट (UG), पोस्टग्रेजुएट (PG) और AICTE स्वीकृत कोर्सेस उपलब्ध हैं:\n\n" \
                        f"**1. स्नातक (UG) कोर्सेस (3 वर्ष):**\n" \
                        f"• बी.एससी. कंप्यूटर साइंस (B.Sc. CS) — 60 सीटें\n" \
                        f"• बी.एससी. इंफॉर्मेशन टेक्नोलॉजी (B.Sc. IT) — 120 सीटें\n" \
                        f"• बी.सी.ए. (BCA - AICTE) — 60 सीटें\n" \
                        f"• बी.बी.ए. (BBA - AICTE) — 60 सीटें\n" \
                        f"• बी.कॉम (General, BAF, BBI, BFM, BTM)\n" \
                        f"• बी.ए. (History, Economics, BAMMC, Film & TV)\n" \
                        f"• बी.एससी. (Chemistry, Botany, Zoology)\n\n" \
                        f"**2. स्नातकोत्तर (PG) कोर्सेस (2 वर्ष):**\n" \
                        f"• एम.एससी. आईटी, एम.एससी. केमिस्ट्री, एम.कॉम, एम.ए. इतिहास\n\n" \
                        f"🛠️ **कौशल केंद्र:** 20 जॉब-ओरिएंटेड KLiC सर्टिफिकेट कोर्सेस।"
            elif lang == "gu":
                reply = f"🎓 **વંદે માતરમ ડિગ્રી કોલેજના અભ્યાસક્રમો (Courses):**\n\n" \
                        f"કોલેજમાં મુંબઈ યુનિવર્સિટી સાથે સંલગ્ન અંડરગ્રેજ્યુએટ (UG), પોસ્ટગ્રેજ્યુએટ (PG) અને AICTE માન્ય કોર્સ ઉપલબ્ધ છે:\n\n" \
                        f"**1. અંડરગ્રેજ્યુએટ (UG) કોર્સ (3 વર્ષ):**\n" \
                        f"• B.Sc. CS (કમ્પ્યુટર સાયન્સ) — 60 સીટો\n" \
                        f"• B.Sc. IT (ઇન્ફોર્મેશન ટેકનોલોજી) — 120 સીટો\n" \
                        f"• B.C.A. (AICTE માન્ય) — 60 સીટો\n" \
                        f"• B.B.A. (AICTE માન્ય) — 60 સીટો\n" \
                        f"• B.Com, BAF, BBI, BFM\n" \
                        f"• B.A., BAMMC, ફિલ્મ અને ટીવી પ્રોડક્શન\n\n" \
                        f"**2. પોસ્ટગ્રેજ્યુએટ (PG) કોર્સ (2 વર્ષ):**\n" \
                        f"• M.Sc. IT, M.Sc. કેમિસ્ટ્રી, M.Com, M.A."
            else:
                ug_names = [f"• {p['name']}" for p in self.programmes["ug_programmes"]]
                pg_names = [f"• {p['name']}" for p in self.programmes["pg_programmes"]]
                aicte_names = [f"• {p['name']}" for p in self.programmes["aicte_programmes"]]
                reply = f"🎓 **Programmes Offered at Vande Mataram Degree College:**\n\n" \
                        f"**Under-Graduate (UG) Programmes (12):**\n" + "\n".join(ug_names) + "\n\n" \
                        f"**Post-Graduate (PG) Programmes (4):**\n" + "\n".join(pg_names) + "\n\n" \
                        f"**AICTE Approved Programmes (3):**\n" + "\n".join(aicte_names) + "\n\n" \
                        f"🛠️ **VMDC Kaushal Centre:** 20 KLiC skill development courses (120 hrs, Rs. 6000/- each)."
            return {"reply": reply, "source": "Handbook Programmes Offered (p. 2, 24)", "quick_actions": ["B.Sc CS", "B.Sc IT", "BCA", "BBA", "B.Com", "Admission Eligibility"]}

        # Admission Eligibility / Criteria
        if any(k in q for k in ["eligibility", "eligible", "criteria", "who can apply", "admission kaise", "kaise le"]) or \
           (lang in ["mr", "hi", "gu"] and any(k in q for k in ["पात्रता", "प्रवेश कसा", "પ્રવેશ કેવી રીતે"])):
            if lang == "hinglish":
                reply = f"📝 **Admission Eligibility Criteria (VMDC):**\n\n" \
                        f"• **General UG Degree:** 12th Std (HSC) pass from Maharashtra Board ya equivalent.\n" \
                        f"• **B.Sc. CS & B.Sc. IT:** 12th Science pass with **Mathematics** compulsory subject.\n" \
                        f"• **B.C.A. / B.B.A. (AICTE):** 12th pass in Any Stream (Science / Commerce / Arts).\n" \
                        f"• **B.Com / BAF / BMS:** 12th pass in Commerce / Science / Arts.\n" \
                        f"• **Trust Preference:** JMF Trust ke school ke students ko admission me preference di jaati hai."
            elif lang == "mr":
                reply = f"📝 **प्रवेश पात्रता निकष (VMDC):**\n\n" \
                        f"• **सर्वसाधारण पदवी (UG):** १२ वी (HSC) उत्तीर्ण.\n" \
                        f"• **B.Sc. CS आणि B.Sc. IT:** १२ वी विज्ञान उत्तीर्ण सह **गणित (Mathematics)** विषय अनिवार्य.\n" \
                        f"• **B.C.A. / B.B.A.:** कोणत्याही शाखेतून १२ वी उत्तीर्ण.\n" \
                        f"• **B.Com / BAF / BMS:** १२ वी वाणिज्य / विज्ञान / कला उत्तीर्ण."
            elif lang == "hi":
                reply = f"📝 **प्रवेश पात्रता मानदंड (VMDC):**\n\n" \
                        f"• **सामान्य यूजी डिग्री:** 12वीं (HSC) उत्तीर्ण।\n" \
                        f"• **बी.एससी. CS और IT:** 12वीं साइंस में **गणित** अनिवार्य।\n" \
                        f"• **बी.सी.ए. और बी.बी.ए.:** किसी भी स्ट्रीम से 12वीं उत्तीर्ण।\n" \
                        f"• **बी.कॉम / बीएएफ:** 12वीं कॉमर्स / साइंस / आर्ट्स उत्तीर्ण।"
            elif lang == "gu":
                reply = f"📝 **પ્રવેશ પાત્રતા (VMDC):**\n\n" \
                        f"• **સામાન્ય UG ડિગ્રી:** 12મું (HSC) પાસ.\n" \
                        f"• **B.Sc. CS & IT:** 12મું સાયન્સ સાથે **ગણિત** વિષય ફરજિયાત.\n" \
                        f"• **BCA / BBA:** કોઈપણ પ્રવાહમાં 12મું પાસ."
            else:
                reply = f"📝 **General Admission Eligibility (VMDC):**\n\n" \
                        f"• **First Year Degree College:** Passed 12th Std (H.S.C.) conducted by Maharashtra State Board or equivalent.\n" \
                        f"• **B.Sc. CS / B.Sc. IT:** Passed 12th Std with **Mathematics** as a required subject.\n" \
                        f"• **B.C.A. / B.B.A. (AICTE):** Passed 12th Std in any stream.\n" \
                        f"• **B.Com / BAF / BMS:** Passed 12th Std Commerce / Arts / Science."
            return {"reply": reply, "source": "Handbook Admission Guidelines (p. 12)", "quick_actions": ["Required Documents", "Admission Process", "Courses"]}

        # Required Documents
        if any(k in q for k in ["documents", "document", "papers", "paper", "kagaj", "kagad"]) or \
           (lang in ["mr", "hi", "gu"] and any(k in q for k in ["कागदपत्रे", "दस्तावेज", "દસ્તાવેજ"])):
            if lang == "hinglish":
                reply = f"📋 **Admission ke liye zaroori Documents:**\n\n" \
                        f"• Aadhar Card & PAN Card ki photocopy\n" \
                        f"• 10th (SSC) & 12th (HSC) Original Marksheet + 3 Attested copies\n" \
                        f"• Leaving Certificate (LC) Original + copies\n" \
                        f"• Caste Certificate & Income Certificate (agar applicable ho)\n" \
                        f"• 5 Passport-size color photos\n" \
                        f"• Mumbai University Pre-Admission Online Registration Form.\n\n" \
                        f"📌 *Original documents jama karne se pehle kam se kam 10 xerox copies apne paas sambhal kar rakhein.*"
            elif lang == "mr":
                reply = f"📋 **प्रवेशासाठी आवश्यक कागदपत्रे:**\n\n" \
                        f"• आधार कार्ड आणि पॅन कार्ड प्रत\n" \
                        f"• १० वी आणि १२ वी मूळ गुणपत्रिका + ३ साक्षांकित प्रती\n" \
                        f"• शाळा सोडल्याचा दाखला (LC) मूळ प्रत\n" \
                        f"• जात प्रमाणपत्र आणि उत्पन्न प्रमाणपत्र (लागू असल्यास)\n" \
                        f"• ५ पासपोर्ट आकाराचे फोटो\n" \
                        f"• मुंबई विद्यापीठ पूर्व-नोंदणी फॉर्म."
            elif lang == "hi":
                reply = f"📋 **प्रवेश के लिए आवश्यक दस्तावेज:**\n\n" \
                        f"• आधार कार्ड और पैन कार्ड की प्रति\n" \
                        f"• 10वीं और 12वीं की मूल अंकतालिका + 3 सत्यापित प्रतियां\n" \
                        f"• स्कूल लीविंग सर्टिफिकेट (LC) मूल प्रति\n" \
                        f"• जाति प्रमाण पत्र एवं आय प्रमाण पत्र (यदि लागू हो)\n" \
                        f"• 5 पासपोर्ट साइज फोटो एवं विश्वविद्यालय प्री-रजिस्ट्रेशन फॉर्म।"
            elif lang == "gu":
                reply = f"📋 **પ્રવેશ માટે જરૂરી દસ્તાવેજો:**\n\n" \
                        f"• આધાર કાર્ડ અને પાન કાર્ડ\n" \
                        f"• 10મું અને 12મું ઓરિજિનલ માર્કશીટ + 3 ઝેરોક્ષ\n" \
                        f"• શાળા છોડ્યાનું પ્રમાણપત્ર (LC)\n" \
                        f"• જાતિ અને આવકનું પ્રમાણપત્ર (જો લાગુ હોય)\n" \
                        f"• 5 પાસપોર્ટ સાઇઝ ફોટો."
            else:
                docs = self.admissions.get("first_year_eligibility", {}).get("documents_required", [])
                doc_str = "\n".join([f"• {d}" for d in docs[:8]])
                reply = f"📋 **Documents Required for First Year Admission:**\n\n{doc_str}\n\n" \
                        f"📌 *Preserve at least 10 attested photocopies before submitting originals.*"
            return {"reply": reply, "source": "Handbook Admission Guidelines (p. 12, 13)", "quick_actions": ["Admission Eligibility", "Scholarship Documents", "Fee Refund Rules"]}

        # Scholarships & Financial Aid
        if any(k in q for k in ["scholarship", "freeship", "financial aid", "paisa", "aid", "welfare"]) or \
           (lang in ["mr", "hi", "gu"] and any(k in q for k in ["शिष्यवृत्ती", "छात्रवृत्ति", "સ્કોલરશિપ"])):
            if lang == "hinglish":
                reply = f"🎓 **Scholarships & Student Welfare Schemes (VMDC):**\n\n" \
                        f"1. **JMF Scholarship:** Rs. 500 se Rs. 10,000/- tak ki financial help deserving aur economically backward students ke liye (kisi bhi caste/religion ke liye).\n" \
                        f"2. **Government Scholarships:** SC/ST/OBC/VJNT/EBC students ke liye MahaDBT portal dwara.\n" \
                        f"3. **Book Bank Scheme:** Pure saal ke liye free textbook sets aur competitive exam study material.\n" \
                        f"4. **Yuva Raksha Insurance:** Rs. 40/- me 100% accident death/disability aur medical coverage.\n" \
                        f"5. **Student Start-Up Seed Capital:** Business start karne ke liye Rs. 5,000/- tak seed money."
            elif lang == "mr":
                reply = f"🎓 **शिष्यवृत्ती आणि विद्यार्थी कल्याण योजना (VMDC):**\n\n" \
                        f"१. **JMF शिष्यवृत्ती:** गरजू आणि गुणवंत विद्यार्थ्यांसाठी रु. ५०० ते रु. १०,०००/- पर्यंत मदत.\n" \
                        f"२. **शासकीय शिष्यवृत्ती:** SC/ST/OBC/VJNT/EBC प्रवर्गांसाठी महाडीबीटी द्वारे.\n" \
                        f"३. **बुक बँक योजना:** वर्षभरासाठी मोफत पाठ्यपुस्तके.\n" \
                        f"४. **युवा रक्षा विमा:** रु. ४०/- वार्षिक हप्त्यात अपघात विमा संरक्षण.\n" \
                        f"५. **स्टार्टअप निधी:** व्यवसाय सुरू करण्यासाठी रु. ५,०००/- पर्यंत बीजभांडवल."
            elif lang == "hi":
                reply = f"🎓 **छात्रवृत्ति एवं कल्याणकारी योजनाएं:**\n\n" \
                        f"1. **JMF छात्रवृत्ति:** आर्थिक रूप से कमजोर छात्रों के लिए रु. 500 से रु. 10,000/- तक की सहायता।\n" \
                        f"2. **सरकारी छात्रवृत्ति:** SC/ST/OBC/EBC छात्रों हेतु महाडीबीटी पोर्टल द्वारा।\n" \
                        f"3. **बुक बैंक योजना:** पूरे वर्ष हेतु मुफ्त पाठ्यपुस्तकें।\n" \
                        f"4. **युवा रक्षा बीमा:** मात्र रु. 40/- वार्षिक में दुर्घटना बीमा कवर।"
            elif lang == "gu":
                reply = f"🎓 **સ્કોલરશિપ અને વિદ્યાર્થી યોજનાઓ:**\n\n" \
                        f"1. **JMF સ્કોલરશિપ:** જરૂરિયાતમંદ વિદ્યાર્થીઓ માટે રૂ. 500 થી 10,000/-.\n" \
                        f"2. **સરકારી સ્કોલરશિપ:** SC/ST/OBC/EBC માટે.\n" \
                        f"3. **બુક બેંક યોજના:** મફત પુસ્તકોની સુવિધા."
            else:
                jmf = next((s for s in self.welfare["schemes"] if s["id"] == "jmf_scholarship"), {})
                reply = f"🎓 **Scholarships & Welfare Schemes at VMDC:**\n\n" \
                        f"1. **JMF Scholarship:** {jmf.get('amount')} grant for deserving and economically backward students.\n\n" \
                        f"2. **Government Freeships/Scholarships:** For SC/ST/OBC/VJNT/SBC/EBC categories via MahaDBT.\n\n" \
                        f"3. **Students' Aid Fund & Book Bank:** Provides textbook sets and fee assistance (Rs. 5/yr).\n\n" \
                        f"4. **Yuva Raksha Insurance Scheme:** Rs. 40/- annual premium for complete contingency coverage."
            return {"reply": reply, "source": "Handbook Student Welfare (p. 17, 19, 23)", "quick_actions": ["JMF Scholarship", "Book Bank", "Required Documents"]}

        # Attendance & Rules
        if any(k in q for k in ["attendance", "attend", "hazari", "75%", "timing", "discipline", "rules"]) or \
           (lang in ["mr", "hi", "gu"] and any(k in q for k in ["उपस्थिती", "नियम", "હાજરી", "નિયમો"])):
            if lang == "hinglish":
                reply = f"📅 **College Attendance & Campus Rules:**\n\n" \
                        f"• **75% Attendance Compulsory:** Mumbai University Ordinance O. 6086 ke mutabik har student ki kam se kam **75% attendance** hona zaroori hai.\n" \
                        f"• **Bunking Policy:** Lectures bunk karna strictly prohibited hai.\n" \
                        f"• **Campus Entry:** Valid College I-Card, Notebook aur Pen ke bina entry nahi milti.\n" \
                        f"• **Discipline:** Library aur exam me mobile strictly band rakhna zaroori hai."
            elif lang == "mr":
                reply = f"📅 **महाविद्यालयीन उपस्थिती व नियम:**\n\n" \
                        f"• **७५% उपस्थिती अनिवार्य:** मुंबई विद्यापीठ अध्यादेश O. 6086 नुसार प्रत्येक विद्यार्थ्याची किमान **७५% उपस्थिती** आवश्यक आहे.\n" \
                        f"• **शिस्तपालन:** वैध ओळखपत्र (I-Card), वही आणि पेन असणे अनिवार्य आहे.\n" \
                        f"• **मोबाईल बंदी:** परीक्षा आणि ग्रंथालयात मोबाईल वापरण्यास सक्त मनाई आहे."
            elif lang == "hi":
                reply = f"📅 **कॉलेज उपस्थिति एवं नियम:**\n\n" \
                        f"• **75% उपस्थिति अनिवार्य:** मुंबई विश्वविद्यालय अध्यादेश O. 6086 के तहत कम से कम **75% उपस्थिति** आवश्यक है।\n" \
                        f"• **आई-कार्ड:** कॉलेज में प्रवेश के लिए वैध आई-कार्ड अनिवार्य है।\n" \
                        f"• **अनुशासन:** कक्षाओं से बंक मारना दंडनीय है।"
            elif lang == "gu":
                reply = f"📅 **કોલેજ હાજરી અને નિયમો:**\n\n" \
                        f"• **75% હાજરી ફરજિયાત:** મુંબઈ યુનિવર્સિટી નિયમ O. 6086 મુજબ 75% હાજરી જરૂરી છે.\n" \
                        f"• **આઈ-કાર્ડ:** કોલેજ કેમ્પસમાં આઈડી કાર્ડ ફરજિયાત છે."
            else:
                reply = f"📅 **College Attendance Rule:**\n\n" \
                        f"• **Mandatory Requirement:** Under **Ordinance No. O. 6086 of the University of Mumbai**, every student is strictly required to attend **at least 75%** of the total number of Lectures and Practicals.\n\n" \
                        f"• **Discipline:** Valid I-Card is mandatory for campus entry."
            return {"reply": reply, "source": "Handbook College Rules (p. 15, Ordinance O.6086)", "quick_actions": ["College Rules", "Discipline", "ATKT Rules"]}

        # Fee Refund
        if any(k in q for k in ["refund", "cancellation", "cancel", "fee refund", "money back", "paise wapas"]):
            rules_tbl = self.admissions.get("cancellation_and_refund_rules", {}).get("schedule", [])
            if lang == "hinglish":
                reply = f"💰 **Admission Cancellation & Fee Refund Rules (Ordinance 0.2859):**\n\n" \
                        f"• **Before College Reopening:** Rs. 1000/- deduction (Baaki amount refund).\n" \
                        f"• **Day 1 to 30 Days:** 20% of total fees deduction.\n" \
                        f"• **Day 31 to 60 Days:** 30% of total fees deduction.\n" \
                        f"• **Day 61 to 90 Days:** 50% of total fees deduction.\n" \
                        f"• **After 90 Days:** No refund.\n\n" \
                        f"📌 Cancellation ke liye original fee receipt aur I-Card jama karna hota hai."
            else:
                tbl_lines = [f"• **{r['period']}**:\n  ↳ *Deduction:* {r['deduction']} ({r['refund_percentage']})" for r in rules_tbl]
                reply = f"💰 **Fee Refund Rules (University of Mumbai Ordinance 0.2859):**\n\n" + "\n\n".join(tbl_lines)
            return {"reply": reply, "source": "Handbook Fee Refund (p. 14)", "quick_actions": ["Admission", "Services", "Scholarships"]}

        # Step 3: Semantic Fallback search or LLM
        search_matches = self.search_all(raw_query)
        if search_matches:
            top = search_matches[0]
            context_snip = "\n".join([f"- {m['title']}: {m['snippet']}" for m in search_matches[:3]])
            
            # Try Gemini LLM if available
            llm_reply = self._call_gemini_llm(raw_query, lang, context_snip)
            if llm_reply:
                return {
                    "reply": llm_reply,
                    "source": "College AI (Multilingual Engine)",
                    "quick_actions": ["Courses", "Admissions", "Scholarships", "Services"]
                }
            
            # Smart Dynamic NLP formatting in detected language
            if lang == "hinglish":
                reply = f"ℹ️ **{top['title']} ke bare me jankari:**\n\n{top['snippet']}\n\n👉 Aap iske baare me aur details ke liye [yahan check karein]({top['url']}) ya college office me sampark karein."
            elif lang == "mr":
                reply = f"ℹ️ **{top['title']} बद्दल माहिती:**\n\n{top['snippet']}\n\n👉 अधिक माहितीसाठी [येथे क्लिक करा]({top['url']}) किंवा कॉलेज कार्यालयाशी संपर्क साधा."
            elif lang == "hi":
                reply = f"ℹ️ **{top['title']} के बारे में जानकारी:**\n\n{top['snippet']}\n\n👉 अधिक विवरण के लिए [यहाँ देखें]({top['url']}) या कॉलेज कार्यालय से संपर्क करें।"
            elif lang == "gu":
                reply = f"ℹ️ **{top['title']} વિશે માહિતી:**\n\n{top['snippet']}\n\n👉 વધુ વિગતો માટે [અહીં ક્લિક કરો]({top['url']}) અથવા કોલેજ ઓફિસનો સંપર્ક કરો."
            else:
                reply = f"ℹ️ **{top['title']} Information:**\n\n{top['snippet']}\n\n👉 For more details, visit [this section]({top['url']}) or visit the college administrative office."
                
            return {
                "reply": reply,
                "source": top["source"],
                "quick_actions": ["Courses", "Admissions", "Scholarships", "Services"]
            }

        # Step 4: Multilingual Unmatched Fallback
        if lang == "hinglish":
            reply = "Is vishay par specific jankari mere pass handbook me uplabdh nahi hai. Aap Vande Mataram Degree College ke administrative office me ya counter par direct sampark kar sakte hain."
        elif lang == "mr":
            reply = "या विषयाबद्दल सध्या हस्तपुस्तिकेत विशिष्ट माहिती उपलब्ध नाही. अधिकृत मार्गदर्शनासाठी कृपया महाविद्यालयाच्या प्रशासकीय कार्यालयाशी संपर्क साधा."
        elif lang == "hi":
            reply = "इस विषय पर सटीक जानकारी वर्तमान में उपलब्ध नहीं है। आधिकारिक मार्गदर्शन के लिए कृपया कॉलेज के प्रशासनिक कार्यालय से संपर्क करें।"
        elif lang == "gu":
            reply = "આ વિષય પર ચોક્કસ માહિતી ઉપલબ્ધ નથી. કૃપા કરીને અધિકૃત માહિતી માટે કોલેજ વહીવટી કચેરીનો સંપર્ક કરો."
        else:
            reply = "I don't currently have that specific information in my college knowledge base. You can check directly with the college administrative office or an administrator for official guidance."

        return {
            "reply": reply,
            "source": "Knowledge Base (Unmatched)",
            "quick_actions": ["Courses Available", "Admission Process", "Fee Refund Rules", "Student Services", "Scholarships", "College Rules"]
        }
