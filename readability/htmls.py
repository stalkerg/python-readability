from .cleaners import normalize_spaces, clean_attributes
from .encoding import get_encoding
from lxml.html import tostring
import lxml.html

import re
import logging

utf8_parser = lxml.html.HTMLParser(encoding='utf-8')

def build_doc(page):
    if isinstance(page, str):
        enc = None
        page_unicode = page
    else:
        enc = get_encoding(page) or 'utf-8'
        page_unicode = page.decode(enc, 'replace')
    doc = lxml.html.document_fromstring(page_unicode.encode('utf-8', 'replace'), parser=utf8_parser)
    return doc, enc

def js_re(src, pattern, flags, repl):
    return re.compile(pattern, flags).sub(src, repl.replace('$', '\\'))


def normalize_entities(cur_title):
    entities = {
        u'\u2014': '-',
        u'\u2013': '-',
        u'&mdash;': '-',
        u'&ndash;': '-',
        u'\u00A0': ' ',
        u'\u00AB': '"',
        u'\u00BB': '"',
        u'&quot;': '"',
    }
    for c, r in entities.items():
        if c in cur_title:
            cur_title = cur_title.replace(c, r)

    return cur_title

def norm_title(title):
    return normalize_entities(normalize_spaces(title))

def get_title(doc):
    title = doc.find('.//title')
    if title is None or title.text is None or len(title.text) == 0:
        return ''

    return norm_title(title.text)

def add_match(collection, text, orig):
    text = norm_title(text)
    if len(text.split()) >= 2 and len(text) >= 15:
        if text.replace('"', '') in orig.replace('"', ''):
            collection.add(text)

def shorten_title(doc):
    title = doc.find('.//title')
    if title is None or title.text is None or len(title.text) == 0:
        return ''

    title = orig = norm_title(title.text)

    candidates = set()

    for item in ['.//h1', './/h2', './/h3']:
        for e in list(doc.iterfind(item)):
            if e.text:
                add_match(candidates, e.text, orig)
            if e.text_content():
                add_match(candidates, e.text_content(), orig)

    for item in ['#title', '#head', '#heading', '.pageTitle', '.news_title', '.title', '.head', '.heading', '.contentheading', '.small_header_red']:
        for e in doc.cssselect(item):
            if e.text:
                add_match(candidates, e.text, orig)
            if e.text_content():
                add_match(candidates, e.text_content(), orig)

    if candidates:
        title = sorted(candidates, key=len)[-1]
    else:
        for delimiter in [' | ', ' - ', ' :: ', ' / ']:
            if delimiter in title:
                parts = orig.split(delimiter)
                if len(parts[0].split()) >= 4:
                    title = parts[0]
                    break
                elif len(parts[-1].split()) >= 4:
                    title = parts[-1]
                    break
        else:
            if ': ' in title:
                parts = orig.split(': ')
                if len(parts[-1].split()) >= 4:
                    title = parts[-1]
                else:
                    title = orig.split(': ', 1)[1]

    if not 15 < len(title) < 150:
        return orig

    return title

def get_body(doc):
    [ elem.drop_tree() for elem in doc.xpath('.//script | .//link | .//style') ]
    raw_html = str(tostring(doc.body or doc))
    try:
        cleaned = clean_attributes(raw_html)
        return cleaned
    except Exception:
        logging.error("cleansing broke html content: %s\n---------\n%s" % (raw_html, cleaned))
        return raw_html

def get_first_image_url(doc):
    images = doc.cssselect('img')
    if images:
        return images[0].get("src")
    else:
        return None

def get_image_from_meta(doc):
    og_image = doc.xpath('/html/head/meta[@property="og:image"]')
    if og_image:
        og_image_content = og_image[0].get("content")
        if og_image_content:
            return og_image_content
    
    twitter_image = doc.xpath('/html/head/meta[@name="twitter:image:src"]')
    if twitter_image:
        twitter_image_content = twitter_image[0].get("content")
        if twitter_image_content:
            return twitter_image_content

    return None

def get_lead(doc):
    paragraphs = doc.cssselect("p")
    if paragraphs:
        lead = paragraphs[0]
        lead = lead.text_content()
        if len(lead) > 50 and len(lead) < 300:
            return lead

    return None