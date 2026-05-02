# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import json

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class MetaSpiderPipeline:
    def process_item(self, item):
        field = ['nid', 'tags']
        line = {key: item[key] for key in field}
        line = json.dumps(line, ensure_ascii=False) + '\n'
        self.file.write(line)
        return item
    
    def open_spider(self):
        self.file = open('tag.jsonl', 'a', encoding='utf-8')

    def close_spider(self):
        self.file.close()
