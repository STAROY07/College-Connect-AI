import unittest
import json
import os
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from app import app, engine

class CollegeConnectTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_20_benchmark_questions(self):
        questions = [
            ("1. What courses are available?", ["UG Programmes", "PG Programmes", "AICTE", "B.Sc. Computer Science", "B.Sc. Information Technology"]),
            ("2. What is B.Sc Computer Science?", ["B.Sc. : Computer Science", "60 Seats", "Mathematics"]),
            ("3. What is B.Sc IT?", ["B.Sc. : Information Technology", "120 Seats", "Mathematics"]),
            ("4. What is the eligibility for admission?", ["H.S.C.", "12th Std", "Maharashtra State Board"]),
            ("5. What documents are required?", ["Aadhar Card", "S.S.C.", "H.S.C.", "Leaving Certificate"]),
            ("6. What scholarships are available?", ["JMF Scholarship", "Rs. 500", "Rs. 10,000", "Students' Aid Fund"]),
            ("7. What is the attendance requirement?", ["75%", "Ordinance No. O. 6086", "University of Mumbai"]),
            ("8. What are the library rules?", ["Identity Card", "7 days", "Rs. 1/-", "Rs. 4/-", "Rs. 50/-"]),
            ("9. What is NSS?", ["National Service Scheme", "120 hours", "10 grace marks"]),
            ("10. What is the railway concession?", ["Kopar station", "25 years", "Ration Card", "05 mins"]),
            ("11. What is a bonafide certificate?", ["Bonafide Certificate", "05 mins", "Roll Number", "Regular Students"]),
            ("12. What is the fee refund rule?", ["Ordinance 0.2859", "Rs. 1500", "20%", "30%", "50%", "60%", "100%"]),
            ("13. What is VMDC Kaushal Centre?", ["VMDC Kaushal Centre", "20", "120 Hours", "Rs. 6000", "JMF Scholarship"]),
            ("14. What are the B.Sc CS subjects?", ["Open source Technologies", "Web Technology", "Cyber & Digital Safety", "Social Media Marketing"]),
            ("15. What are the B.Sc IT subjects?", ["IT_Fundamentals of Computer", "IT_Google Workspace", "IT_PHP DOTNET core", "Data Science"]),
            ("16. What student welfare facilities are available?", ["JMF Scholarship", "Students Welfare Fund", "Students' Aid Fund", "Yuva Raksha", "Start-Up"]),
            ("17. What committees are there?", ["40", "Examination Committee", "NAAC", "IQAC", "Discipline Committee"]),
            ("18. What activities are conducted?", ["PRERNOTSAV", "Job Melas", "Gymkhana", "Cultural"]),
            ("19. What services are available?", ["24", "Railway Concession", "Bonafide", "Turnaround"]),
            ("20. What is the secret recipe for Martian space cheese pizza?", ["I don't currently have that specific information in my college knowledge base"])
        ]

        print("\n================= RUNNING 20 BENCHMARK CHATBOT TESTS =================")
        for q, expected_keywords in questions:
            res = self.app.post("/chat", json={"message": q})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            reply = data.get("reply", "")
            
            # Verify that at least one/all key expected strings are present
            matched = any(kw.lower() in reply.lower() for kw in expected_keywords)
            print(f"\n[Q] {q}\n[A Preview] {reply[:120]}...\n[Source] {data.get('source')}\n[Match OK]: {matched}")
            self.assertTrue(matched, f"Failed match for query '{q}'. Reply was: {reply}")

    def test_routes_status(self):
        routes = ["/", "/programmes", "/courses", "/admissions", "/services", "/student-life", "/scholarships-welfare", "/rules", "/kaushal-centre", "/updates", "/admin"]
        print("\n================= TESTING HTTP ROUTES =================")
        for r in routes:
            res = self.app.get(r)
            self.assertEqual(res.status_code, 200, f"Route {r} returned {res.status_code}")
            print(f"Route {r} -> HTTP 200 OK")

    def test_api_search(self):
        print("\n================= TESTING SEARCH API =================")
        queries = ["bonafide", "scholarship", "computer science", "refund", "attendance", "railway"]
        for q in queries:
            res = self.app.get(f"/api/search?q={q}")
            self.assertEqual(res.status_code, 200)
            results = res.get_json().get("results", [])
            self.assertTrue(len(results) > 0, f"No search results for query '{q}'")
            print(f"Search '{q}' returned {len(results)} items: top title = {results[0]['title']}")

    def test_admin_dynamic_update_workflow(self):
        print("\n================= TESTING DYNAMIC ADMIN KNOWLEDGE WORKFLOW =================")
        # 1. Add new government result portal
        payload = {
            "title": "New Government Result Portal 2026",
            "category": "Portals / Results",
            "content": "The college now uses XYZ Maharashtra portal (xyzportal.gov.in) for result checking.",
            "source": "College Office",
            "url": "https://xyzportal.gov.in"
        }
        res = self.app.post("/admin/api/add-update", json=payload)
        self.assertEqual(res.status_code, 200)
        item_id = res.get_json().get("item", {}).get("id")

        # 2. Ask chatbot about the newly added portal
        chat_res = self.app.post("/chat", json={"message": "Where can I check my result on the portal?"})
        self.assertEqual(chat_res.status_code, 200)
        chat_data = chat_res.get_json()
        print(f"Chatbot response for dynamic update: {chat_data['reply']}")
        self.assertIn("New Government Result Portal", chat_data["reply"])

        # 3. Clean up the test update
        del_res = self.app.post("/admin/api/delete-update", json={"id": item_id})
        self.assertEqual(del_res.status_code, 200)
        print("Dynamic update cleanup verified.")

if __name__ == "__main__":
    unittest.main()
