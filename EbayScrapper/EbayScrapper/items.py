from scrapy.item import Item, Field

class EbayscrapperItem(Item):
    # Product information:
    title = Field()
    price = Field()
    link = Field()
    description = Field()
    image_urls = Field()  # For ImagesPipeline: list of image URLs
    product_id = Field()  # Unique product identifier
    category = Field()    # Category derived from breadcrumbs or search context
    condition = Field()
    brand = Field()
    location = Field()    # Item location
    return_policy = Field()
    
    # Seller information
    seller_name = Field()
    seller_positive_feedback_percentage = Field() # e.g. "99.5% Positive feedback"
    seller_feedback_count = Field() # e.g., "(12345)"
    seller_link = Field()
    top_rated_seller = Field() # Boolean or text

    # Meta Search Info
    derived_from_keyword = Field()
    category_context_from_search = Field() # Category used in search URL