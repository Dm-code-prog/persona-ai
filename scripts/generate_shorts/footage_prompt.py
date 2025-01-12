def get_footage_prompt(lib, script: str) -> str:
    return f"""
You are an AI assistant that enriches a plain text script by inserting special footage tags.

## Footage Library
We have a library of footages, each line is:
  filename.ext,tag1,tag2,... up to 5 tags

Library:   
 {lib}
 
 Use these lines to find the best match for each insertion. 
- If we want a “video,” pick from `.mp4` or `.mov` only. 
- If we want a “photo,” pick from `.jpg`, `.png`, `.gif` only. 
- No file can be reused twice. 
- If no good match is found, use `"not_found"`.

## Requirements
1. Insert `{{"video": "filename.ext"}}` every ~2–4 seconds of text. 
   - Assume we have ~2–3 spoken words per second. 
   - So roughly 5–8 words of text in between each video tag.
2. Insert `{{"photo": "filename.ext"}}` for important or highlight moments (1-second length). 
   - Usually for big announcements or transitions.
3. The final script must preserve the original text. **Do not remove** or change words, only add tags.
4. The final format for each inserted footage is exactly:
{{“video”: “some_file.mp4”}}
{{“photo”: “some_file.png”}}

with a single filename (no arrays).

## Script
Here is the plain text script we want to enrich:

---
{script}
---

## Output
Return one text block that includes the original script (unchanged) plus the newly inserted tags.
Each inserted tag must be carefully chosen from the library by best matching context to tags.
No file can be reused. If we fail to find a match, use `"not_found"`.
    """
