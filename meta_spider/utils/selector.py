import re


banner_pattern = re.compile(r'background:url\((http.+)\)')

def get_clean(response, selector):
    return response.css(selector + '::text').get().strip()

def get_clean_all(response, selector) -> list | None:
    return [text.strip() for text in response.css(selector + '::text').getall()]

def get_attribute(response, selector, attribute='src'):
    return response.css(f'{selector}::attr({attribute})').get()

def get_banner(response) -> str:
    try:
        s = response.css('.d-banner::attr(style)').get()
        return banner_pattern.search(s).group(1) 
    except:
        return ''