from readability import Document
import urllib.parse
import urllib.request
import hashlib
import os

class AppURLopener(urllib.request.FancyURLopener):
	version = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.67 Safari/537.36"

url_list = [
	"http://www.pcf.city.hiroshima.jp/outline/index.php?l=E&id=34",
	"http://www.salon.com/2014/07/06/bbc_staff_ordered_to_stop_giving_equal_air_time_to_climate_deniers/?utm_source=facebook&utm_medium=socialflow",
	"http://www.reddit.com/r/AskReddit/comments/2a0nfq/people_with_pm_me_usernames_what_is_the_most/",
	"http://www.telegraph.co.uk/culture/tvandradio/bbc/10944629/BBC-staff-told-to-stop-inviting-cranks-on-to-science-programmes.html",
	"http://www.reddit.com/r/Showerthoughts/comments/2a0l99/i_wonder_if_the_queen_of_england_has_ever_eaten_a/",
	"http://www.reddit.com/r/TwoXChromosomes/comments/2a0eeh/probirth_prolife_or_prochoice_a_very_simple/",
	"http://www.reddit.com/r/LifeProTips/comments/29ztqj/lpt_if_a_company_gives_you_a_verbal_unofficial/",
	"http://www.reddit.com/r/IAmA/comments/29z6da/iama_blind_man_who_suffered_a_gunshot_wound_to/",
	"http://www.mediaite.com/online/super-pac-to-get-rid-of-super-pacs-raises-5m/",
	"http://techcrunch.com/2014/07/06/charge-your-phone-before-flying-tsa-will-now-block-dead-devices-at-some-airports/?utm_campaign=fb&ncid=fb",
	"http://www.scientificamerican.com/article/the-largest-extinction-in-earth-s-history-may-have-been-caused-by-microbes/",
	"http://bigstory.ap.org/article/soviet-defectors-trove-kgb-secrets-made-public",
	"http://www.reddit.com/r/personalfinance/comments/29zmz4/is_medical_school_worth_it_for_300000_debt_and_4/"
]

if __name__ ==  "__main__":
	try:
		os.mkdir("test_by_urls")
	except:
			pass

	urllib._urlopener = AppURLopener()

	for url in url_list:
		url_hex = hashlib.md5(url.encode("utf-8")).hexdigest()[:4]
		print("Start parse url: %s by hash: %s"%(url, url_hex))
		try:
			request = urllib.request.urlopen(url)
		except:
			print("Error load url")
			continue
		html = request.read().decode("utf-8")
		doc = Document(html)
		doc.parse(["summary", "title", "lead"])

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
