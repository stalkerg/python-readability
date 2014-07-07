#!/usr/bin/env python
import re
import sys

from lxml.etree import tostring
from lxml.etree import tounicode
from lxml.html import document_fromstring
from lxml.html import fragment_fromstring

from .cleaners import clean_attributes
from .cleaners import html_cleaner
from .htmls import build_doc
from .htmls import get_body
from .htmls import get_title
from .htmls import shorten_title
from .htmls import get_first_image_url
from .htmls import get_image_from_meta
from .htmls import get_lead

import logging
from urllib.parse import urlparse


class Unparseable(ValueError):
    pass

def contains_one_or_more_tags(node, *tags):
    """
    >>> contains_one_or_more_tags(fragment_fromstring('<div/>'), 'div')
    False
    >>> contains_one_or_more_tags(fragment_fromstring('<div>   </div>'), 'div', 'p')
    False
    >>> contains_one_or_more_tags(fragment_fromstring('<div>  fsfdsff<a>oi mundo</a></div>'), 'p', 'a')
    True
    >>> contains_one_or_more_tags(fragment_fromstring('<div>  fsfdsff<a>oi mundo</a></div>'), 'a')
    True
    """
    for tag in tags:
        if node.find('.//%s' % tag) is not None:
            return True
    return False


def has_text(node):
    """
    >>> has_text(fragment_fromstring('<div/>'))
    False
    >>> has_text(fragment_fromstring('<div>   </div>'))
    False
    >>> has_text(fragment_fromstring('<div>  fsfdsff </div>'))
    True
    >>> has_text(fragment_fromstring('<div>  fsfdsff<a>oi mundo</a></div>'))
    True
    """
    if node.text is not None and node.text.strip():
        return True
    else:
        return False


def is_empty_node(node):
    """
    >>> is_empty_node(fragment_fromstring('<div/>'))
    True
    >>> is_empty_node(fragment_fromstring('<div>   </div>'))
    True
    >>> is_empty_node(fragment_fromstring('<div>  fsfdsff </div>'))
    False
    >>> is_empty_node(fragment_fromstring('<div><a>Ola mundo</a></div>'))
    False
    >>> is_empty_node(fragment_fromstring('<div>  fsfdsff<a>oi mundo</a></div>'))
    False
    """
    return not has_text(node) and not node.getchildren()

def describe(node, depth=1):
    if not hasattr(node, 'tag'):
        return "[%s]" % type(node)
    name = node.tag
    if node.get('id', ''):
        name += '#' + node.get('id')
    if node.get('class', ''):
        name += '.' + node.get('class').replace(' ', '.')
    if name[:4] in ['div#', 'div.']:
        name = name[3:]
    if depth and node.getparent() is not None:
        return name + ' - ' + describe(node.getparent(), depth - 1)
    return name


def clean(text):
    text = re.sub('\s*\n\s*', '\n', text)
    text = re.sub('[ \t]{2,}', ' ', text)
    return text.strip()


def text_length(i):
    return len(clean(i.text_content() or ""))

regexp_type = type(re.compile('hello, world'))

def compile_pattern(elements, mode=re.U):
    if not elements:
        return None
    if isinstance(elements, regexp_type):
        return elements
    if isinstance(elements, str):
        elements = elements.split(',')
    return re.compile(u'|'.join([re.escape(x.lower()) for x in elements]), mode)

class Document:
    """Class to build a etree document out of html."""
    UNLIKELY_CANDIDATES = [
        "combx", "comment", "community",
        "disqus", "extra|foot", "header",
        "menu", "remark", "rss",
        "shoutbox", "sidebar", "sponsor",
        "ad-break", "agegate", "pagination",
        "pager", "popup", "tweet",
        "twitter"
    ]
    LIKELY_CANDIDATES = [
        "and", "article", "body", 
        "column", "main", "shadow"
    ]
    POSITIVE_STRINGS = [
        "article", "body", "content", 
        "entry", "hentry", "main", 
        "page", "pagination", "post", 
        "text", "blog", "story"
    ]
    NEGATIVE_STRINGS = [
        "combx", "comment", "com-",
        "contact", "foot", "footer",
        "footnote", "masthead", "media",
        "meta", "outbrain", "promo", 
        "related", "scroll", "shoutbox",
        "sidebar", "sponsor", "shopping",
        "tags", "tool", "widget"
    ]


    REGEXES = {
        'unlikelyCandidatesRe': compile_pattern(UNLIKELY_CANDIDATES, re.I),
        'okMaybeItsACandidateRe': compile_pattern(LIKELY_CANDIDATES, re.I),
        'positiveRe': compile_pattern(POSITIVE_STRINGS, re.I),
        'negativeRe': compile_pattern(NEGATIVE_STRINGS, re.I),
        'shareLinks': re.compile("twitter.com\/share|pinterest.com\/pin\/create|facebook.com\/sharer", re.I),
        'divToPElementsRe': re.compile('<(a|blockquote|dl|div|img|ol|p|pre|table|ul)', re.I)
    }

    def __init__(self, input, 
            base_url=None, debug=False,
            positive_keywords=None, negative_keywords=None, 
            min_text_length=25, retry_length=250):
        """Generate the document

        :param input: string of the html content.
        :type input: unicode
        :param base_url: will allow adjusting links to be absolute
        :type base_url: unicode
        :param positive_keywords: the list of positive search patterns in classes and ids
        :type positive_keywords: list
        :param negative_keywords: the list of negative search patterns in classes and ids
        :type negative_keywords: list
        :param debug: output debug messages
        :type debug: bool
        :param min_text_length: minimum text size
        :type min_text_length: int
        :param retry_length: acceptable length of the text
        :type retry_length: int


        Also positive_keywords and negative_keywords could be a regexp.
        """
        self.input = input
        self.base_url = base_url
        if self.base_url:
            parsed_url = urlparse(self.base_url)
            self.base_url = "%s://%s" % (parsed_url.scheme, parsed_url.hostname)
        self.enable_debug = debug
        self.min_text_length = min_text_length
        self.retry_length = retry_length
        self.encoding = None
        self.positive_keywords = compile_pattern(positive_keywords)
        self.negative_keywords = compile_pattern(negative_keywords)

        #Cache attributes
        self.__orig_html = None
        self.__cut_html = None
        self.__title = None
        self.__short_title = None
        self.__content = None
        self.__summary = None
        self.__lead = None
        self.__first_image_url = None
        self.__main_image_url = None
        self.__clean_html = None

    def __parse(self, input):
        doc, self.encoding = build_doc(input)
        doc = html_cleaner.clean_html(doc)

        if self.base_url:
            doc.make_links_absolute(self.base_url, resolve_base_href=True)
        else:
            doc.resolve_base_href()
        return doc

    def __detect_req(self, params_list, match, req):
        if match in params_list and not req in params_list:
            params_list.append(req)

    def parse(self, params_list=["title", "summary", "content", "lead", "first_image_url", "main_image_url"], html_partial=False):
        #Detect params
        full_params_list = list(params_list)
        self.__detect_req(full_params_list, "lead", "summary")
        self.__detect_req(full_params_list, "main_image_url", "summary")
        self.__detect_req(full_params_list, "first_image_url", "summary")

        #Pre parsing
        self.__orig_html = self.__parse(self.input)
        self.__cut_html = self.__parse(self.input)

        if "content" in full_params_list:
            self.__content = get_body(self.__parse(self.input))
        if "title" in full_params_list:
            self.__title = get_title(self.__orig_html)
        if "short_title" in full_params_list:
            self.__short_title = shorten_title(self.__orig_html)
        if "summary" in full_params_list:
            self.__summary = self.__get_summary(html_partial)
        if "lead" in full_params_list:
            self.__lead = get_lead(self.__cut_html)
        if "first_image_url" in full_params_list:
            self.__first_image_url = get_first_image_url(self.__cut_html)
        if "main_image_url" in full_params_list:
            if not self.__first_image:
                self.__first_image_url = get_first_image_url(self.__cut_html)
            meta_image = get_image_from_meta(self.__orig_html)
            self.__main_image_url = meta_image or self.__first_image_url

    def content(self):
        return self.__content

    def title(self):
        return self.__title

    def short_title(self):
        return self.__short_title

    def first_image_url(self):
        return self.__first_image_url

    def main_image_url(self):
        return self.__main_image_url

    def lead(self):
        return self.__lead

    def summary(self):
        return self.__summary

    def __get_summary(self, html_partial=False):
        """Generate the summary of the html docuemnt

        :param html_partial: return only the div of the document, don't wrap
        in html and body tags.

        """
        try:
            ruthless = True
            while True:
                for i in self.__tags(self.__cut_html, 'script', 'style'):
                    i.drop_tree()
                for i in self.__tags(self.__cut_html, 'body'):
                    i.set('id', 'readabilityBody')
                if ruthless:
                    self.__remove_unlikely_candidates()
                self.__transform_misused_divs_into_paragraphs()
                candidates = self.__score_paragraphs()

                best_candidate = self.__select_best_candidate(candidates)

                if best_candidate:
                    article = self.__get_article(candidates, best_candidate,
                            html_partial=html_partial)
                else:
                    if ruthless:
                        self.debug("ruthless removal did not work. ")
                        ruthless = False
                        self.debug(
                            ("ended up stripping too much - "
                             "going for a safer _parse"))
                        # try again
                        continue
                    else:
                        self.debug(
                            ("Ruthless and lenient parsing did not work. "
                             "Returning raw html"))
                        article = self.__cut_html.find('body')
                        if article is None:
                            article = self.__cut_html
                cleaned_article = self.__sanitize(article, candidates)
                article_length = len(cleaned_article or '')
                of_acceptable_length = article_length >= self.retry_length
                if ruthless and not of_acceptable_length:
                    ruthless = False
                    # Loop through and try again.
                    continue
                else:
                    return cleaned_article
        except Exception as e:
            logging.exception('error getting summary: ')
            raise Unparseable(str(e))

    def __get_article(self, candidates, best_candidate, html_partial=False):
        # Now that we have the top candidate, look through its siblings for
        # content that might also be related.
        # Things like preambles, content split by ads that we removed, etc.
        sibling_score_threshold = max([10, best_candidate['content_score'] * 0.2])

        # create a new html document with a html->body->div
        if html_partial:
            output = fragment_fromstring('<div/>')
        else:
            output = document_fromstring('<div/>')
        best_elem = best_candidate['elem']
        for sibling in best_elem.getparent().getchildren():
            # in lxml there no concept of simple text
            # if isinstance(sibling, NavigableString): continue
            append = False
            if sibling is best_elem:
                append = True
            sibling_key = sibling  # HashableElement(sibling)
            if sibling_key in candidates and \
                candidates[sibling_key]['content_score'] >= sibling_score_threshold:
                append = True

            if sibling.tag == "p":
                link_density = self.__get_link_density(sibling)
                node_content = sibling.text or ""
                node_length = len(node_content)

                if node_length > 80 and link_density < 0.25:
                    append = True
                elif node_length <= 80 \
                    and link_density == 0 \
                    and re.search('\.( |$)', node_content):
                    append = True

            if append:
                # We don't want to append directly to output, but the div
                # in html->body->div
                if html_partial:
                    output.append(sibling)
                else:
                    output.getchildren()[0].getchildren()[0].append(sibling)
        #if output is not None:
        #    output.append(best_elem)
        return output

    def __select_best_candidate(self, candidates):
        sorted_candidates = sorted(list(candidates.values()), key=lambda x: x['content_score'], reverse=True)
        for candidate in sorted_candidates[:5]:
            elem = candidate['elem']
            self.debug("Top 5 : %6.3f %s" % (
                candidate['content_score'],
                describe(elem)))

        if len(sorted_candidates) == 0:
            return None

        best_candidate = sorted_candidates[0]
        return best_candidate

    def __get_link_density(self, elem):
        link_length = 0
        for i in elem.findall(".//a"):
            link_length += text_length(i)
        
        total_length = text_length(elem)
        return float(link_length) / max(total_length, 1)

    def __score_paragraphs(self, ):
        candidates = {}
        ordered = []
        for elem in self.__tags(self.__cut_html, "p", "pre", "td"):
            parent_node = elem.getparent()
            if parent_node is None:
                continue
            grand_parent_node = parent_node.getparent()

            inner_text = clean(elem.text_content() or "")
            inner_text_len = len(inner_text)

            # If this paragraph is less than 25 characters
            # don't even count it.
            if inner_text_len < self.min_text_length:
                continue

            if parent_node not in candidates:
                candidates[parent_node] = self.__score_node(parent_node)
                ordered.append(parent_node)

            if grand_parent_node is not None and grand_parent_node not in candidates:
                candidates[grand_parent_node] = self.__score_node(
                    grand_parent_node)
                ordered.append(grand_parent_node)

            content_score = 1
            content_score += len(inner_text.split(','))
            content_score += min((inner_text_len / 100), 3)
            
            candidates[parent_node]['content_score'] += content_score
            if grand_parent_node is not None:
                candidates[grand_parent_node]['content_score'] += content_score / 2.0

        # Scale the final candidates score based on link density. Good content
        # should have a relatively small link density (5% or less) and be
        # mostly unaffected by this operation.
        for elem in ordered:
            candidate = candidates[elem]
            ld = self.__get_link_density(elem)
            score = candidate['content_score']
            self.debug("Candidate: %6.3f %s link density %.3f -> %6.3f" % (
                score,
                describe(elem),
                ld,
                score * (1 - ld)))
            candidate['content_score'] *= (1 - ld)

        return candidates

    def __class_weight(self, e):
        weight = 0
        for feature in [e.get('class', None), e.get('id', None)]:
            if feature:
                if self.REGEXES['negativeRe'].search(feature):
                    weight -= 25

                if self.REGEXES['positiveRe'].search(feature):
                    weight += 25

                if self.positive_keywords and self.positive_keywords.search(feature):
                    weight += 25

                if self.negative_keywords and self.negative_keywords.search(feature):
                    weight -= 25

        if self.positive_keywords and self.positive_keywords.match('tag-'+e.tag):
            weight += 25

        if self.negative_keywords and self.negative_keywords.match('tag-'+e.tag):
            weight -= 25

        return weight

    def __score_node(self, elem):
        content_score = self.__class_weight(elem)
        name = elem.tag.lower()
        if name == "div":
            content_score += 5
        elif name in ["pre", "td", "blockquote"]:
            content_score += 3
        elif name in ["address", "ol", "ul", "dl", "dd", "dt", "li", "form"]:
            content_score -= 3
        elif name in ["h1", "h2", "h3", "h4", "h5", "h6", "th"]:
            content_score -= 5
        return {
            'content_score': content_score,
            'elem': elem
        }

    def debug(self, *a):
        if self.enable_debug:
            logging.debug(*a)

    def __remove_unlikely_candidates(self):
        for elem in self.__cut_html.iter():
            s = "%s %s" % (elem.get('class', ''), elem.get('id', ''))
            if len(s) < 2:
                continue
            #self.debug(s)
            if self.REGEXES['unlikelyCandidatesRe'].search(s) and (not self.REGEXES['okMaybeItsACandidateRe'].search(s)) and elem.tag not in ['html', 'body']:
                self.debug("Removing unlikely candidate - %s" % describe(elem))
                elem.drop_tree()

    def __transform_misused_divs_into_paragraphs(self):
        for elem in self.__tags(self.__cut_html, 'div'):
            # transform <div>s that do not contain other block elements into
            # <p>s
            #FIXME: The current implementation ignores all descendants that
            # are not direct children of elem
            # This results in incorrect results in case there is an <img>
            # buried within an <a> for example
            if not self.REGEXES['divToPElementsRe'].search(
                    str(b''.join(map(tostring, list(elem))))):
                #self.debug("Altering %s to p" % (describe(elem)))
                elem.tag = "p"
                #print "Fixed element "+describe(elem)

        for elem in self.__tags(self.__cut_html, 'div'):
            if elem.text and elem.text.strip():
                p = fragment_fromstring('<p/>')
                p.text = elem.text
                elem.text = None
                elem.insert(0, p)
                #print "Appended "+tounicode(p)+" to "+describe(elem)

            for pos, child in reversed(list(enumerate(elem))):
                if child.tail and child.tail.strip():
                    p = fragment_fromstring('<p/>')
                    p.text = child.tail
                    child.tail = None
                    elem.insert(pos + 1, p)
                    #print "Inserted "+tounicode(p)+" to "+describe(elem)
                if child.tag == 'br':
                    #print 'Dropped <br> at '+describe(elem)
                    child.drop_tree()

    def __tags(self, node, *tag_names):
        for tag_name in tag_names:
            for e in node.findall('.//%s' % tag_name):
                yield e

    def __reverse_tags(self, node, *tag_names):
        for tag_name in tag_names:
            for e in reversed(node.findall('.//%s' % tag_name)):
                yield e

    def __get_clean_html(self):
         return clean_attributes(tounicode(self.__cut_html))

    def __normalize_images_path(self, image):
        if not image.attrib["src"].startswith(("//", "https://", "http://")):
            image.attrib["src"] = "%s%s" % (self.base_url, image.attrib["src"])

    def __drop_node_and_empty_parents(self, node):
        """
        Removes given element and hierarchy if everything is empty
        """
        while True:
            parent = node.getparent()
            if parent is not None:
                node.drop_tree()
                if is_empty_node(parent):
                    node = parent
                    continue
            break

    def __move_childrens_to_root(self, node):
        while True:
            if len(node) == 1 and node[0].tag == "div":
                node_for_remove = node[0]
                for i, elem in enumerate(node_for_remove):
                     node.insert(i, elem)
                node.remove(node_for_remove)
                continue
            break

        while True:
            for i, elem in enumerate(node):
                if elem.tag == "div":
                    if len(elem) == 1:
                        node.insert(i, elem[0])
                        break
            else:
                break

    def __sanitize(self, node, candidates):
        for header in self.__tags(node, "h1", "h2", "h3", "h4", "h5", "h6", "p"):
            if self.__class_weight(header) < 0 or self.__get_link_density(header) > 0.33:
                self.__drop_node_and_empty_parents(header)

        # removes empty paragraphs and removes unwanted lead spaces
        for elem in self.__tags(node, "p"):
            if elem.text:
                elem.text = elem.text.lstrip()
            if is_empty_node(elem):
                self.__drop_node_and_empty_parents(elem)

        for elem in self.__tags(node, "a"):
            if "href" in elem.attrib and self.REGEXES['shareLinks'].search(elem.attrib["href"]) or is_empty_node(elem):
                self.__drop_node_and_empty_parents(elem)

        for elem in self.__tags(node, "span"):
            if is_empty_node(elem):
                self.__drop_node_and_empty_parents(elem)

        for elem in self.__tags(node, "form", "iframe", "textarea", "button"):
            self.__drop_node_and_empty_parents(elem)

        for elem in self.__tags(node, "strong"):
            elem.tag = "b"

        for elem in self.__tags(node, "em"):
            elem.tag = "i"

        for elem in self.__tags(node, "img"):
            for attr in ["width", "height"]:
                try:
                    if attr in elem.attrib and int(elem.attrib[attr]) < 70:
                        self.__drop_node_and_empty_parents(elem)
                        break 
                except:
                    pass
            else:
                if "src" in elem.attrib:
                    self.__normalize_images_path(elem)
                else:
                    self.__drop_node_and_empty_parents(elem)

        allowed = {}
        # Conditionally clean <table>s, <ul>s, and <div>s
        for el in self.__reverse_tags(node, "table", "ul", "div"):
            if el in allowed:
                continue
            weight = self.__class_weight(el)
            if el in candidates:
                content_score = candidates[el]['content_score']
                #print '!',el, '-> %6.3f' % content_score
            else:
                content_score = 0
            tag = el.tag

            if weight + content_score < 0:
                self.debug("Cleaned %s with score %6.3f and weight %-3s" %
                    (describe(el), content_score, weight, ))
                el.drop_tree()
            elif el.text_content().count(",") < 10:
                counts = {}
                for kind in ['p', 'img', 'li', 'a', 'embed', 'input']:
                    counts[kind] = len(el.findall('.//%s' % kind))
                counts["li"] -= 100

                # Count the text length excluding any surrounding whitespace
                content_length = text_length(el)
                link_density = self.__get_link_density(el)
                parent_node = el.getparent()
                if parent_node is not None:
                    if parent_node in candidates:
                        content_score = candidates[parent_node]['content_score']
                    else:
                        content_score = 0
                to_remove = False
                reason = ""

                #if el.tag == 'div' and counts["img"] >= 1:
                #    continue
                if counts["p"] and counts["img"] > counts["p"]:
                    reason = "too many images (%s)" % counts["img"]
                    to_remove = True
                elif counts["li"] > counts["p"] and tag != "ul" and tag != "ol":
                    reason = "more <li>s than <p>s"
                    to_remove = True
                elif counts["input"] > (counts["p"] / 3):
                    reason = "less than 3x <p>s than <input>s"
                    to_remove = True
                elif content_length < (self.min_text_length) and (counts["img"] == 0 or counts["img"] > 2):
                    reason = "too short content length %s without a single image" % content_length
                    to_remove = True
                elif weight < 25 and link_density > 0.2:
                        reason = "too many links %.3f for its weight %s" % (
                            link_density, weight)
                        to_remove = True
                elif weight >= 25 and link_density > 0.5:
                    reason = "too many links %.3f for its weight %s" % (
                        link_density, weight)
                    to_remove = True
                elif (counts["embed"] == 1 and content_length < 75) or counts["embed"] > 1:
                    reason = "<embed>s with too short content length, or too many <embed>s"
                    to_remove = True
                    #find x non empty preceding and succeeding siblings
                    i, j = 0, 0
                    x = 1
                    siblings = []
                    for sib in el.itersiblings():
                        #self.debug(sib.text_content())
                        sib_content_length = text_length(sib)
                        if sib_content_length:
                            i =+ 1
                            siblings.append(sib_content_length)
                            if i == x:
                                break
                    for sib in el.itersiblings(preceding=True):
                        #self.debug(sib.text_content())
                        sib_content_length = text_length(sib)
                        if sib_content_length:
                            j =+ 1
                            siblings.append(sib_content_length)
                            if j == x:
                                break
                    #self.debug(str(siblings))
                    if siblings and sum(siblings) > 1000:
                        to_remove = False
                        self.debug("Allowing %s" % describe(el))
                        for desnode in self.__tags(el, "table", "ul", "div"):
                            allowed[desnode] = True

                if to_remove:
                    self.debug("Cleaned %6.3f %s with weight %s cause it has %s." %
                        (content_score, describe(el), weight, reason))
                    #print tounicode(el)
                    #self.debug("pname %s pweight %.3f" %(pname, pweight))
                    self.__drop_node_and_empty_parents(el)



        root = node.find(".//body")
        if root is None:
            root = node
        self.__move_childrens_to_root(root)

        self.__cut_html = node
        return self.__get_clean_html()

