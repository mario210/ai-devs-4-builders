import requests
import re
import ai.tools.image

from urllib.parse import urljoin
from ai.agent import Agent

def fetch_doc_and_links(url: str, session: requests.Session = None):
    main_url = url

    full_content = ""
    
    # Use the provided session or create a new one for unauthenticated requests
    requester = session if session else requests

    try:
        # Fetch the main document
        print(f"Fetching {main_url}...")
        response = requester.get(main_url)
        response.raise_for_status()
        main_text = response.text
        full_content += f"=== CONTENT FROM {main_url} ===\n"
        full_content += main_text + "\n\n"
        
        # 1. Find custom include directives: [include file="filename"]
        include_links = re.findall(r'\[include\s+file="(.*?)"\]', main_text)
        
        # 2. Find standard markdown links/images: [text](url) or ![alt](url)
        # This regex `\]\((.*?)\)` captures content within parentheses following a ']'
        # It's broad but effective for markdown links.
        standard_links = re.findall(r'\]\((.*?)\)', main_text)
        
        all_potential_links = include_links + standard_links
        
        cleaned_links = []
        for link in all_potential_links:
            # Assuming the regex extracts the clean URL/filename.
            # The original `link.split()[0]` could be problematic if the URL itself contained spaces.
            url_part = link 
            if url_part.startswith('#'): # Skip anchor links within the same document
                continue
            absolute_url = urljoin(main_url, url_part)
            cleaned_links.append(absolute_url)

        unique_links = sorted(list(set(cleaned_links)))

        for link in unique_links:
            if link == main_url: # Avoid re-fetching the main document
                continue
                
            try:
                print(f"Checking linked content: {link}...")
                link_res = requester.get(link, stream=True)
                link_res.raise_for_status()

                content_type = link_res.headers.get('Content-Type', '').lower()
                
                if 'text' in content_type or 'json' in content_type or \
                   link.endswith(('.md', '.txt', '.csv')):
                    
                    text_content = link_res.text
                    full_content += f"=== TEXT CONTENT FROM {link} ===\n"
                    full_content += text_content + "\n\n"

                elif 'image' in content_type:
                    full_content += f"=== MEDIA/BINARY FOUND AT {link} ===\n"
                    full_content += f"Type: {content_type}\n"
                    print(f"  -> Analyzing image...")
                    
                    image_content = link_res.content # type: ignore
                    agent = Agent()
                    description = ai.tools.image.analyze_image_bytes(agent, image_content)

                    print(f"--- Image Description ({link}) ---\n{description}\n-----------------------------")

                    full_content += f"--- IMAGE DESCRIPTION ---\n{description}\n"
                    full_content += "---------------------------\n\n"
                    
                else:
                    full_content += f"=== MEDIA/BINARY FOUND AT {link} ===\n"
                    full_content += f"Type: {content_type}\n"
                    full_content += "Content not displayed (binary).\n\n"
                    
                link_res.close()

            except requests.RequestException as e:
                print(f"Failed to fetch {link}: {e}")
                full_content += f"=== FAILED TO FETCH {link} ===\n\n"

    except requests.RequestError as e:
        print(f"Error fetching main document: {e}")
        return None

    return full_content