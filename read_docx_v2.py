import zipfile
import xml.etree.ElementTree as ET
import sys

def read_docx(file_path):
    try:
        with zipfile.ZipFile(file_path) as docx:
            xml_content = docx.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        text = []
        for paragraph in tree.iterfind('.//w:p', ns):
            texts = [node.text for node in paragraph.iterfind('.//w:t', ns) if node.text]
            if texts:
                text.append(''.join(texts))
        return '\n'.join(text)
    except Exception as e:
        return f"Error reading file {file_path}: {e}"

if __name__ == "__main__":
    file_path = r"c:\Study\QLDA\Kế hoạch dự án (1).docx"
    text = read_docx(file_path)
    with open(r"c:\Study\QLDA\full_docx_output.txt", "w", encoding="utf-8") as f:
        f.write(text)
