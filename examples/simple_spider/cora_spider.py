import re
import urllib.parse
import json

from ruia import *
from db import MotorBase


class ItemLocationStore(Item):
    links = AttrField(css_select='#liste_mag_region li a', attr='href', many=True)


class CatInNav(Item):
    links = HtmlField(css_select='.nav-niv1', many=True)


class SubCatItem(Item):
    links = AttrField(css_select='li a', attr='href', many=True)


class ItemInCat(Item):
    id = AttrField(css_select='.item',  attr='id', many=True)
    links = AttrField(css_select='.item .picture a', attr='href', many=True)


class CoraItem(Item):
    id = AttrField(css_select='.idProduit', attr='value')
    name = TextField(css_select='h1 a')
    brand = AttrField(css_select='.picto li img', attr='title')
    price = TextField(css_select='.prix-produit')

    async def clean_title(self, value):
        return value


class CoraSpider(Spider):
    start_urls = ['https://www.coradrive.fr']
    concurrency = 10
    seen_urls = set()
    accepted_cat = [
        '/le-marche/',
        '/nos-regions',
        '/bebes/',
        '/produits-surgeles/',
        '/boissons/',
        '/epicerie-sucree/',
        '/epicerie-salee/',
        '/animalerie/',
    ]
    regex_cat = re.compile(r'\b(?:{0})\b'.format('|'.join(accepted_cat)))
    items_parsed = []

    async def parse(self, response: Response):
        local_stores = await ItemLocationStore.get_item(html=response.html)
        #async for url in ItemLocationStore.get_items(html=response.html):
        urls = [urllib.parse.urljoin(response.url, url) for url in local_stores.links]
        for url in urls:
            print(url)
        async for url in self.multiple_request(urls, is_gather=True):
            yield Request(url=url.url, callback=self.parse_local_store)

    async def parse_local_store(self, response: Response):
        print('subcat')
        cat_item = await CatInNav.get_item(html=response.html)
        for cat in cat_item.links:
            subcats = await SubCatItem.get_item(html=cat)
            for subcat in subcats.links:
                if self.regex_cat.search(subcat):
                    yield Request(subcat, callback=self.parse_page_items)

    async def parse_page_items(self, response: Response):
        items = await ItemInCat.get_item(html=response.html)
        for item in range(len(items.links)):
            print(items.links[item], items.id[item])
            if items.id[item] not in self.items_parsed:
                yield Request(items.links[item], callback=self.parse_item)
                self.items_parsed.append(items.id[item])


    async def parse_item(self, response: Response):
        async for label in CoraItem.get_items(html=response.html):
            print(label.id, label.name, label.brand, label.price)

if  __name__ == '__main__':
    CoraSpider.start()
