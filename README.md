This code is under the Apache License 2.0.  http://www.apache.org/licenses/LICENSE-2.0

This is Python3 fork of https://github.com/buriy/python-readability and 
https://github.com/ftzeng/python-readability (some python3 support).
I support only Python3 and drop Python2.x. 
This is not only Python3 fork. I added new features and some fixing like "lead" or "main_image_url". 

Installation::

    pip install git+https://github.com/stalkerg/python-readability

Usage::

```python
from readability.readability import Document
import urllib

html = urllib.urlopen(url).read()
readable_article = Document(html).summary()
readable_title = Document(html).short_title()
```

```

Document() __init__ arguments:
 - **input**: input html as text
 - **base_url**: will allow adjusting links to be absolute
 - **debug**: output debug messages
 - **min_text_length**: minimum text size
 - **retry_length**: acceptable length of the text

 - **positive_keywords**: the list of positive search patterns in classes and ids,
 for example: ["news-item", "block"]
 - **negative_keywords**: the list of negative search patterns in classes and ids,
 for example: ["mysidebar", "related", "ads"]

