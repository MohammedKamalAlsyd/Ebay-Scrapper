# EbayScrapper/pipelines.py

from scrapy.pipelines.images import ImagesPipeline
from scrapy.utils.python import to_bytes
import hashlib
import scrapy

class ProductIdImagesPipeline(ImagesPipeline):

    def file_path(self, request, response=None, info=None, *, item=None):
        """
        Overrides the default file_path method to include the product_id as a folder name.
        """
        if item and 'product_id' in item:
            # Create a folder named after the product ID
            product_id_folder = item['product_id']
            image_guid = hashlib.sha1(to_bytes(request.url)).hexdigest()
            # The path will be: IMAGES_STORE / product_id_folder / image_guid.jpg
            return f'{product_id_folder}/{image_guid}.jpg'
        
        # Fallback to default behavior if product_id is not available
        return super().file_path(request, response=response, info=info, item=item)

    def get_media_requests(self, item, info):
        # This method is called to get requests for media (images in this case).
        # We need to ensure 'product_id' is present in the item when this method is called.
        if 'image_urls' in item and 'product_id' in item:
            for image_url in item['image_urls']:
                # The 'item' is passed to file_path, so ensure product_id is in it
                yield scrapy.Request(image_url, meta={'product_id': item['product_id']})