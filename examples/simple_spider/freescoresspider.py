import re
import urllib.parse
import logging
import os

from ruia import *
import aiofiles
import aiohttp

logging.getLogger('freescore')


class LinkItem(Item):
    link = AttrField(css_select='a', attr='href', many=True)


class ScoreItem(Item):
    title = TextField(css_select='span[itemprop*=itemreviewed] span')
    artist = TextField(css_select='span[itemprop*=itemreviewed]')
    downloads = AttrField(css_select='a.zone_dnl_lien', attr='href', many=True)


class FreeScoresSpider(Spider):
    start_urls = ['http://www.free-scores.com/partitions_libres.php']
    concurrency = 30
    seen_urls = set()
    matching_menu = re.compile('http://www.free-scores.com/partitions_libres.php')
    matching_score_url = re.compile('http://www.free-scores.com/partitions_telecharger.php')

    async def parse(self, response: Response):
        print('encore')
        print(response.url)
        next_urls = []
        links = await LinkItem.get_item(html=response.html)
        for link in links.link:
            url = urllib.parse.urljoin(response.url, link)
            if '#' in url:
                pass
            if url in self.seen_urls:
                pass
            if url in next_urls:
                pass
            else:
                if self.matching_menu.match(url):
                    next_urls.append(url)
                elif self.matching_score_url.match(url):
                    next_urls.append(url)
                else:
                    pass

        async for link in self.multiple_request(next_urls, is_gather=True):
            if self.matching_menu.match(str(link.url)):
                yield Request(url=link.url, callback=self.parse)
            elif self.matching_score_url.match(str(link.url)):
                score_info = await ScoreItem.get_item(html=link.html)
                print('parsing score')
                # [print(download) for download in score_info.downloads]
                dirname = f'~/Documents/free_scores/{score_info.artist}/{score_info.title}'
                if not os.path.exists(dirname):
                    os.makedirs(dirname)
                else:
                    pass

                async with aiohttp.ClientSession() as session:
                    for download in score_info.downloads:
                        async with session.get(download) as resp:
                            f = await aiofiles.open(f'{dirname}/{resp.content_disposition.filename}', mode='wb')
                            await f.write(await resp.read())
                            await f.close()
            else:
                pass
            self.seen_urls.add(link.url)


if __name__ == '__main__':
    FreeScoresSpider.start()
