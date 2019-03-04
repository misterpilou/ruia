from ruia import *
import re
import urllib.parse
import asyncio
import json

from db import MotorBase


class RecipeUrl(Item):
    link = AttrField(css_select='a', attr='href', many=True)

    '''async def clean_link(self,  link):
        return link'''


class RecipeItem(Item):
    title = TextField(css_select='.main-title')
    ingredients = HtmlField(css_select='.recipe-ingredients__list__item', many=True)
    recipe_preparations = TextField(css_select='.recipe-preparation__list__item', many=True)


class RecipeIngredient(Item):
    quantity = TextField(css_select='.recipe-ingredient-qt', many=True)
    ingredients = TextField(css_select='.ingredient', many=True)


class MarmitonSpider(Spider):
    start_urls = ['https://www.marmiton.org/recettes/recette_omelette-savoyarde_88251.aspx']
    concurrency = 10
    seen_urls = set()
    matching_url = re.compile('https://www.marmiton.org/recettes/')
    recipes = dict()
    k = 0
    mongodb = MotorBase().get_db('recipes')

    async def parse(self, response: Response):
        recipes_urls = []
        links = await RecipeUrl.get_item(html=response.html)
        for link in links.link:
            if '#' in link:
                pass
            next_url = urllib.parse.urljoin(response.url, link)
            if next_url in self.seen_urls:
                pass
            else:
                if self.matching_url.match(next_url):
                    recipes_urls.append(next_url)
                else:
                    print(f'{next_url} not matching')
                    self.seen_urls.add(next_url)

        async for recipe in self.multiple_request(recipes_urls, is_gather=True):
            print(recipe)
            yield self.parse_recipe(recipe)
            for url in recipes_urls:
                yield Request(url=url, callback=self.parse)
                self.seen_urls.add(url)

    async def parse_recipe(self, response):

        ingredients = dict()
        steps_preparation = dict()
        item_all = await RecipeItem.get_item(html=response.html)
        title = item_all.title
        ing = [await RecipeIngredient.get_item(html=item) for item in item_all.ingredients]
        i, j = 0, 0
        for inl in ing:
            ingredients.update({f'ingredients{i}': [inl.quantity, inl.ingredients]})
            i += 1
        for it in item_all.recipe_preparations:
            steps_preparation.update({f'step{j}': it})
            j += 1
        self.recipes.update({f'{title}': ((inl for inl in ingredients), (step_prep for step_prep in steps_preparation))})
        #print(title, ingredients, steps_preparation)
        try:
            recipes_dumped = json.dumps({title: (ingredients, steps_preparation)}, ensure_ascii=False).encode('utf8')
            json_recipes = json.loads(recipes_dumped)
            await self.mongodb.marmiton.insert_one(json_recipes)
        except Exception as e:
            print(e)
        self.k += 1
        print(f'Number of parsing {self.k}')


if __name__ == '__main__':
    MarmitonSpider.start()
