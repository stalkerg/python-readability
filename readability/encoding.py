import re
import chardet

def get_encoding(page):
    # Regex for XML and HTML Meta charset declaration
    charset_re = re.compile(b'<meta.*?charset=["\']*(.+?)["\'>]', flags=re.I)
    pragma_re = re.compile(b'<meta.*?content=["\']*;?charset=(.+?)["\'>]', flags=re.I)
    xml_re = re.compile(b'^<\?xml.*?encoding=["\']*(.+?)["\'>]')

    declared_encodings = (charset_re.findall(page) +
            pragma_re.findall(page) +
            xml_re.findall(page))

    # Try any declared encodings
    if len(declared_encodings) > 0:
        for declared_encoding in declared_encodings:
            try:
                declared_encoding = declared_encoding.decode("utf-8")
                page.decode(custom_decode(declared_encoding))
                return custom_decode(declared_encoding)
            except UnicodeDecodeError:
                pass

    # Fallback to chardet if declared encodings fail
    text = re.sub(b'</?[^>]*>\s*', b' ', page)
    enc = 'utf-8'
    if not text.strip() or len(text) < 10:
        return enc # can't guess
    res = chardet.detect(text)
    enc = res['encoding']
    #print '->', enc, "%.2f" % res['confidence']
    enc = custom_decode(enc)
    return enc

def custom_decode(encoding):
    """Overrides encoding when charset declaration
       or charset determination is a subset of a larger
       charset.  Created because of issues with Chinese websites"""
    
    if not encoding:
        return "utf-8"
    encoding = encoding.lower()
    alternates = {
        'big5': 'big5hkscs',
        'gb2312': 'gb18030',
        'ascii': 'utf-8',
        'MacCyrillic': 'cp1251',
    }
    if encoding in alternates:
        return alternates[encoding]
    else:
        return encoding
