import asyncio
import httpx
from bs4 import BeautifulSoup
from fpdf import FPDF, XPos, YPos
import re

class NovelPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, "Shine on Me", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(5)

async def fetch_chapter_content(client, url):
    try:
        response = await client.get(url, timeout=20.0)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract Title
        title_tag = soup.find('h1') or soup.find('h2')
        title = title_tag.get_text(strip=True) if title_tag else "Chapter"

        paragraphs = soup.find_all('p')
        clean_paragraphs = []
        
        exclude_keywords = [
            "Previous Chapter", "Next Chapter", "Novel Home", "Read Settings", 
            "Translated and Edited", "OpenNovel", "ReadTheDrama",
            "Your source for novels", "All Rights Reserved", "Privacy Policy",
            "Navigation", "Home", "All Novels", "Request Novel"
        ]

        for p in paragraphs:
            text = p.get_text(strip=True)
            if not text or any(key.lower() in text.lower() for key in exclude_keywords):
                continue
            if len(text) < 5: continue
            clean_paragraphs.append(text)

        return {"title": title, "content": clean_paragraphs}
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

async def main():
    base_url = "https://www.readthedrama.com/novels/shine-on-me"
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        print("🔍 Scanning for chapters...")
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/119.0.0.0'}
        
        resp = await client.get(base_url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. Collect Links
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/'):
                full_url = f"https://www.readthedrama.com{href}"
            elif not href.startswith('http'):
                full_url = f"https://www.readthedrama.com/{href}"
            else:
                full_url = href

            if "shine-on-me" in full_url.lower() and full_url.rstrip('/') != base_url.rstrip('/'):
                if full_url not in links:
                    links.append(full_url)
        
        # 2. NATURAL SORT (Ensures 1, 2, 3... instead of 1, 10, 11...)
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower()
                    for text in re.split('([0-9]+)', s)]
        
        links.sort(key=natural_sort_key)

        if not links:
            print("❌ No chapters found.")
            return

        print(f"📚 Found {len(links)} chapters. Starting PDF compilation...")

        pdf = NovelPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Title Page
        pdf.add_page()
        pdf.set_font("helvetica", "B", 30)
        pdf.ln(80)
        pdf.cell(0, 15, "SHINE ON ME", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("helvetica", "I", 16)
        pdf.cell(0, 10, "A Complete Novel Collection", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # 3. Process Chapters with Explicit Numbering
        for i, link in enumerate(links, 1):
            print(f"📖 Adding Chapter {i}/{len(links)}...")
            chapter = await fetch_chapter_content(client, link)
            
            if chapter and chapter['content']:
                pdf.add_page()
                
                # CHAPTER LABEL (e.g., Chapter 1)
                pdf.set_font("helvetica", "B", 12)
                pdf.set_text_color(100, 100, 100) # Subtle grey for the "Chapter X" label
                pdf.cell(0, 10, f"CHAPTER {i}", align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                
                # CHAPTER TITLE
                pdf.set_font("helvetica", "B", 20)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(0, 12, chapter['title'])
                pdf.ln(5)
                
                # BODY TEXT
                pdf.set_font("helvetica", "", 12)
                for para in chapter['content']:
                    # Clean encoding for PDF
                    safe_text = para.encode('latin-1', 'ignore').decode('latin-1')
                    pdf.multi_cell(0, 8, safe_text)
                    pdf.ln(3) # Paragraph spacing
            
            await asyncio.sleep(0.1)

        pdf.output("Shine_On_Me_Numbered.pdf")
        print(f"\n✨ Success! Your numbered book is ready: Shine_On_Me_Numbered.pdf")

if __name__ == "__main__":
    asyncio.run(main())