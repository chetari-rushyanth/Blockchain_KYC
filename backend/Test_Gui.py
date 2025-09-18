import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import requests
import json
import os

class KYCAPITester:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-KYC API Tester")
        self.root.geometry("1000x650")

        # Default server URL
        self.server_url = tk.StringVar(value="http://127.0.0.1:5000")

        # Server URL input
        ttk.Label(root, text="Flask Server URL:").pack(pady=5, anchor="w")
        ttk.Entry(root, textvariable=self.server_url, width=80).pack(pady=5)

        # Load Routes Button
        ttk.Button(root, text="🔄 Load Routes", command=self.load_routes).pack(pady=5)

        # Endpoint Dropdown
        ttk.Label(root, text="Select Endpoint:").pack(pady=5, anchor="w")
        self.endpoint = tk.StringVar()
        self.endpoint_dropdown = ttk.Combobox(root, textvariable=self.endpoint, width=100)
        self.endpoint_dropdown.pack(pady=5)

        # Method selection
        ttk.Label(root, text="HTTP Method:").pack(pady=5, anchor="w")
        self.method = tk.StringVar(value="GET")
        ttk.Combobox(root, textvariable=self.method, values=["GET", "POST", "PUT"], width=10).pack(pady=5)

        # JSON Body input
        ttk.Label(root, text="Request Body (JSON):").pack(pady=5, anchor="w")
        self.body_text = scrolledtext.ScrolledText(root, width=110, height=8)
        self.body_text.insert(tk.END, "{}")  # default empty JSON
        self.body_text.pack(pady=5)

        # File upload button
        self.files = {}
        ttk.Button(root, text="📂 Upload File(s)", command=self.upload_file).pack(pady=5)

        # Send request button
        ttk.Button(root, text="🚀 Send Request", command=self.send_request).pack(pady=10)

        # Response box
        ttk.Label(root, text="Response:").pack(pady=5, anchor="w")
        self.response_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=120, height=20)
        self.response_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    def load_routes(self):
        """Fetch available routes from /routes"""
        base_url = self.server_url.get().rstrip("/")
        try:
            response = requests.get(base_url + "/routes", timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract paths
            routes = [r["path"] for r in data.get("routes", [])]
            routes.sort()

            self.endpoint_dropdown["values"] = routes
            if routes:
                self.endpoint.set(routes[0])  # select first by default
            messagebox.showinfo("Routes Loaded", f"Loaded {len(routes)} routes.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load routes:\n{e}")

    def upload_file(self):
        """Allow user to pick file(s) for multipart upload"""
        filepaths = filedialog.askopenfilenames(title="Select File(s)")
        if filepaths:
            for filepath in filepaths:
                fname = os.path.basename(filepath)
                self.files[fname] = open(filepath, "rb")
            messagebox.showinfo("Files Selected", f"Uploaded {len(self.files)} file(s).")

    def send_request(self):
        """Send API request"""
        base_url = self.server_url.get().rstrip("/")
        endpoint = self.endpoint.get().strip()
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        url = base_url + endpoint

        method = self.method.get().upper()

        # Parse body
        body = {}
        try:
            if self.body_text.get("1.0", tk.END).strip():
                body = json.loads(self.body_text.get("1.0", tk.END))
        except Exception as e:
            messagebox.showerror("Invalid JSON", f"Request body is not valid JSON.\n\n{e}")
            return

        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                if self.files:
                    response = requests.post(url, data=body, files=self.files, timeout=20)
                else:
                    response = requests.post(url, json=body, timeout=20)
            elif method == "PUT":
                response = requests.put(url, json=body, timeout=20)
            else:
                messagebox.showerror("Invalid Method", "Unsupported HTTP method selected.")
                return

            self.display_response(url, response)

        except requests.exceptions.RequestException as e:
            messagebox.showerror("API Error", f"Failed to reach {url}\n\nError: {e}")

    def display_response(self, url, response):
        """Format and show response"""
        self.response_box.delete(1.0, tk.END)
        self.response_box.insert(tk.END, f"🔗 URL: {url}\n")
        self.response_box.insert(tk.END, f"📌 Status: {response.status_code}\n\n")

        try:
            json_data = response.json()
            formatted = json.dumps(json_data, indent=4)
            self.response_box.insert(tk.END, f"{formatted}\n")
        except Exception:
            self.response_box.insert(tk.END, response.text)


if __name__ == "__main__":
    root = tk.Tk()
    app = KYCAPITester(root)
    root.mainloop()
