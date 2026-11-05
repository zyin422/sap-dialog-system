#!/usr/bin/env python3
"""
generate_qr.py
==============
Generates a vector SVG QR code pointing to the project repository:
https://github.com/zyin422/sap-dialog-system
Uses standard urllib without requiring third-party pip dependencies.
"""

import os
import urllib.request

REPO_URL = "https://github.com/zyin422/sap-dialog-system"
OUTPUT_SVG = os.path.join(os.path.dirname(__file__), "qr_code.svg")

def main():
    api_endpoint = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={REPO_URL}&format=svg"
    print(f"Fetching QR code for: {REPO_URL}")
    try:
        req = urllib.request.Request(
            api_endpoint,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req) as response:
            svg_data = response.read().decode('utf-8')
        with open(OUTPUT_SVG, "w", encoding="utf-8") as f:
            f.write(svg_data)
        print(f"Successfully generated vector QR code: {OUTPUT_SVG}")
    except Exception as e:
        print(f"Error generating QR code via API: {e}")

if __name__ == "__main__":
    main()
