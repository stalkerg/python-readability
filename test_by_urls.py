from readability import Document
import urllib.parse
import urllib.request
import hashlib
import os


class MyDocument(Document):
	def __init__(self, *argc, **argkw):
		super(MyDocument, self).__init__(*argc, **argkw)

	def debug(self, *a):
		print(*a)


class AppURLopener(urllib.request.FancyURLopener):
	version = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.67 Safari/537.36"

if __name__ ==  "__main__":
	try:
		os.mkdir("test_by_urls")
	except:
		pass

	url_list = open(os.path.join("test_by_urls", "urls.txt"))

	urllib._urlopener = AppURLopener()

	for url in url_list:
		url_hex = hashlib.md5(url.encode("utf-8")).hexdigest()[:4]
		print("Start parse url: %s by hash: %s"%(url, url_hex))
		try:
			request = urllib.request.urlopen(url)
		except:
			print("Error load url")
			continue
		html = request.read()
		doc = MyDocument(html, base_url=url)
		try:
			doc.parse(["summary", "title", "lead"], html_partial=True)
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