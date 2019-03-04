import urllib.parse
import json
import re
import math

from ruia import *
from db import MotorBase


class FoodItem(Item):
    links = AttrField(css_select='.grid-item a', attr='href', many=True)


class CarrefourItem(Item):
    name = TextField(css_select='.main-detail-name h1')
    label = TextField(css_select='.main-detail-name .label')
    id = AttrField(css_select='meta[itemprop*=gtin13]', attr='content')
    price_in_euros = AttrField(css_select='span[itemprop*=offers] meta[itemprop=price]', attr='content')
    description_product = HtmlField(css_select='.pdp__right__subhero__secondary', default='null')


class DescriptionProduct(Item):
    badges = TextField(css_select='.product-badges-list span[class*=product-badge-title]', many=True, default='null')
    title_paragraphs = TextField(css_select='.product-block-content h2', many=True)
    paragraphs = TextField(css_select='.product-block-content-paragraph', many=True)
    nutri_title = TextField(css_select='.nutritional-details h2', default='null')
    nutri_energy_label = TextField(css_select='.nutritional-details-energy', default='null')
    nutri_energy_values = TextField(css_select='.nutritional-details-energy-value', many=True, default='null')
    nutriments = HtmlField(css_select='.nutritional-fact', many=True, default='null')


class Nutriments(Item):
    nutri_labels = TextField(css_select='.subtitle')
    nutri_values = TextField(css_select='.nutritional-fact-value')
    others_nutri = TextField(css_select='.label', many=True, default='null')


class PageCounter(Item):
    pages = TextField(css_select='.product-list-header__count')


class CarrefourSpider(Spider):
    start_urls = ['https://www.carrefour.fr/promotions',
                  'https://www.carrefour.fr/offres-du-moment',
                  'https://www.carrefour.fr/r/bio-et-ecologie',
                  'https://www.carrefour.fr/r/fruits-et-legumes',
                  'https://www.carrefour.fr/r/viandes-et-poissons',
                  'https://www.carrefour.fr/r/pains-et-patisseries',
                  'https://www.carrefour.fr/r/cremerie',
                  'https://www.carrefour.fr/r/charcuterie',
                  'https://www.carrefour.fr/r/traiteur',
                  'https://www.carrefour.fr/r/surgeles',
                  'https://www.carrefour.fr/r/epicerie-salee',
                  'https://www.carrefour.fr/r/epicerie-sucree',
                  'https://www.carrefour.fr/r/boissons-et-cave-a-vins',
                  'https://www.carrefour.fr/r/le-monde-de-bebe',
                  'https://www.carrefour.fr/r/animaux']
    concurrency = 8
    i = 0
    mongodb = MotorBase().get_db('recipes')

    async def parse(self, response: Response):
        urls_pages = []
        pages = await PageCounter.get_item(html=response.html)
        num_item = re.match('^\d+', pages.pages).group()
        num_pages = math.ceil(int(num_item)/60)
        for i in range(1, num_pages+1):
            param_page = f'?page={i}'
            url_page = response.url + param_page
            urls_pages.append(url_page)

        async for url in self.multiple_request(urls_pages, is_gather=True):
            yield Request(url=url.url, callback=self.parse_menu)


    async def parse_menu(self, response: Response):
        print('ok')
        print(response.url)
        items = await FoodItem.get_item(html=response.html)
        for item in items.links:
            url = urllib.parse.urljoin(response.url, item)
            yield Request(url=url, callback=self.parse_item)

    async def parse_item(self, response: Response):
        items = await CarrefourItem.get_item(html=response.html)
        item_dict = {'id': items.id,
                     'url': response.url,
                     'name': items.name,
                     'label': items.label,
                     'price': items.price_in_euros}
        if items.description_product is not 'null':
            paras = await DescriptionProduct.get_item(html=items.description_product)
            item_dict.update({'badge': paras.badges})
            for i in range(len(paras.paragraphs)):
                title = paras.title_paragraphs[i]
                content = paras.paragraphs[i].split('<br>')
                item_dict.update({title: content})

            if paras.nutri_title is not 'null':
                nutri_dict = {'valeur_energetique': paras.nutri_energy_values}

                for nutriment in paras.nutriments:
                    nutri = await Nutriments.get_item(html=nutriment)
                    if nutri.others_nutri != 'null' and nutri.others_nutri[0] is not 'null':
                        nutri_dict.update({nutri.nutri_labels: [
                            nutri.nutri_values, {nutri.others_nutri[0]: nutri.others_nutri[1]}
                        ]})
                    else:
                        nutri_dict.update({nutri.nutri_labels: nutri.nutri_values})
                item_dict.update({paras.nutri_title: nutri_dict})

        item_dumped = json.dumps(item_dict, ensure_ascii=False).encode('utf8')
        json_item = json.loads(item_dumped)
        try:
            await self.mongodb.marmiton.insert_one(json_item)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    CarrefourSpider.start()
