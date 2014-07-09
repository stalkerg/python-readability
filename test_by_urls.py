from readability import Document
import urllib.parse
import urllib.request
import hashlib
import os

import io
import gzip
import argparse


class MyDocument(Document):
	def __init__(self, *argc, **argkw):
		super(MyDocument, self).__init__(*argc, **argkw)

	def debug(self, *a):
		print(*a)


if __name__ ==  "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('--count', nargs='?', default=None, help='count test')
	args = parser.parse_args()

	try:
		os.mkdir("test_by_urls")
	except:
		pass

	url_list_file = open(os.path.join("test_by_urls", "urls.txt"))
	url_list = []

	for url in url_list_file:
		url_list.append(url)

	if args.count:
		url_list = url_list[:int(args.count)]

	for url in url_list:
		url_hex = hashlib.md5(url.encode("utf-8")).hexdigest()[:4]
		print("Start parse url: %s by hash: %s"%(url, url_hex))
		try:
			request = urllib.request.Request(url)
			
			request.add_header('Accept-encoding', 'gzip')
			request.add_header('User-Agent', "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.103 Safari/537.36")
			response = urllib.request.urlopen(request)
		except Exception as e:
			print("Error load url %s"%e)
			continue

		html = ""
		if response.info().get('Content-Encoding') == 'gzip':
			buf = io.BytesIO( response.read())
			f = gzip.GzipFile(fileobj=buf)
			html = f.read()
		else:
			html = response.read()

		doc = MyDocument(html, base_url=url)
		try:
			doc.parse(["summary", "title", "lead", "main_image_url"], html_partial=True)
		except Exception as e:
			print(e)

		try:
			os.mkdir(os.path.join("test_by_urls", url_hex))
		except:
			pass

		url_file = open(os.path.join("test_by_urls", url_hex, "url"), "w")
		url_file.write(url)
		url_file.close()

		summary_file = open(os.path.join("test_by_urls", url_hex, "summary.html"), "w")
		summary_file.write(doc.summary() or "")
		summary_file.close()

		title_file = open(os.path.join("test_by_urls", url_hex, "title"), "w")
		title_file.write(doc.title() or "")
		title_file.close()

		lead_file = open(os.path.join("test_by_urls", url_hex, "lead"), "w")
		lead_file.write(doc.lead() or "")
		lead_file.close()

		img_file = open(os.path.join("test_by_urls", url_hex, "img"), "w")
		img_file.write(doc.main_image_url() or "")
		img_file.close()