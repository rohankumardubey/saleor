import graphene
from graphene import relay

from ...core.permissions import DiscountPermissions, OrderPermissions
from ...discount import models
from ..channel import ChannelQsContext
from ..channel.dataloaders import ChannelByIdLoader
from ..channel.types import (
    ChannelContext,
    ChannelContextType,
    ChannelContextTypeWithMetadata,
)
from ..core import types
from ..core.connection import (
    CountableConnection,
    CountableDjangoObjectType,
    create_connection_slice,
)
from ..core.descriptions import ADDED_IN_31
from ..core.fields import ConnectionField
from ..core.scalars import PositiveDecimal
from ..core.types import Money
from ..decorators import permission_required
from ..meta.types import ObjectWithMetadata
from ..product.types import (
    CategoryCountableConnection,
    CollectionCountableConnection,
    ProductCountableConnection,
    ProductVariantCountableConnection,
)
from ..translations.fields import TranslationField
from ..translations.types import SaleTranslation, VoucherTranslation
from .dataloaders import (
    SaleChannelListingBySaleIdAndChanneSlugLoader,
    SaleChannelListingBySaleIdLoader,
    VoucherChannelListingByVoucherIdAndChanneSlugLoader,
    VoucherChannelListingByVoucherIdLoader,
)
from .enums import DiscountValueTypeEnum, VoucherTypeEnum


class SaleChannelListing(CountableDjangoObjectType):
    class Meta:
        description = "Represents sale channel listing."
        model = models.SaleChannelListing
        interfaces = [relay.Node]
        only_fields = ["id", "channel", "discount_value", "currency"]

    @staticmethod
    def resolve_channel(root: models.SaleChannelListing, info, **_kwargs):
        return ChannelByIdLoader(info.context).load(root.channel_id)


class Sale(ChannelContextTypeWithMetadata, CountableDjangoObjectType):
    categories = ConnectionField(
        CategoryCountableConnection,
        description="List of categories this sale applies to.",
    )
    collections = ConnectionField(
        CollectionCountableConnection,
        description="List of collections this sale applies to.",
    )
    products = ConnectionField(
        ProductCountableConnection, description="List of products this sale applies to."
    )
    variants = ConnectionField(
        ProductVariantCountableConnection,
        description=f"{ADDED_IN_31} List of product variants this sale applies to.",
    )
    translation = TranslationField(
        SaleTranslation,
        type_name="sale",
        resolver=ChannelContextType.resolve_translation,
    )
    channel_listings = graphene.List(
        graphene.NonNull(SaleChannelListing),
        description="List of channels available for the sale.",
    )
    discount_value = graphene.Float(description="Sale value.")
    currency = graphene.String(description="Currency code for sale.")

    class Meta:
        default_resolver = ChannelContextType.resolver_with_context
        description = (
            "Sales allow creating discounts for categories, collections or products "
            "and are visible to all the customers."
        )
        interfaces = [relay.Node, ObjectWithMetadata]
        model = models.Sale
        only_fields = ["end_date", "id", "name", "start_date", "type"]

    @staticmethod
    def resolve_categories(root: ChannelContext[models.Sale], info, *_args, **kwargs):
        qs = root.node.categories.all()
        return create_connection_slice(qs, info, kwargs, CategoryCountableConnection)

    @staticmethod
    @permission_required(DiscountPermissions.MANAGE_DISCOUNTS)
    def resolve_channel_listings(root: ChannelContext[models.Sale], info, **_kwargs):
        return SaleChannelListingBySaleIdLoader(info.context).load(root.node.id)

    @staticmethod
    @permission_required(DiscountPermissions.MANAGE_DISCOUNTS)
    def resolve_collections(root: ChannelContext[models.Sale], info, *_args, **kwargs):
        qs = root.node.collections.all()
        qs = ChannelQsContext(qs=qs, channel_slug=root.channel_slug)
        return create_connection_slice(qs, info, kwargs, CollectionCountableConnection)

    @staticmethod
    @permission_required(DiscountPermissions.MANAGE_DISCOUNTS)
    def resolve_products(root: ChannelContext[models.Sale], info, **kwargs):
        qs = root.node.products.all()
        qs = ChannelQsContext(qs=qs, channel_slug=root.channel_slug)
        return create_connection_slice(qs, info, kwargs, ProductCountableConnection)

    @staticmethod
    @permission_required(DiscountPermissions.MANAGE_DISCOUNTS)
    def resolve_variants(root: ChannelContext[models.Sale], info, **kwargs):
        qs = root.node.variants.all()
        qs = ChannelQsContext(qs=qs, channel_slug=root.channel_slug)
        return create_connection_slice(
            qs, info, kwargs, ProductVariantCountableConnection
        )

    @staticmethod
    def resolve_discount_value(root: ChannelContext[models.Sale], info, **_kwargs):
        if not root.channel_slug:
            return None

        return (
            SaleChannelListingBySaleIdAndChanneSlugLoader(info.context)
            .load((root.node.id, root.channel_slug))
            .then(
                lambda channel_listing: channel_listing.discount_value
                if channel_listing
                else None
            )
        )

    @staticmethod
    def resolve_currency(root: ChannelContext[models.Sale], info, **_kwargs):
        if not root.channel_slug:
            return None

        return (
            SaleChannelListingBySaleIdAndChanneSlugLoader(info.context)
            .load((root.node.id, root.channel_slug))
            .then(
                lambda channel_listing: channel_listing.currency
                if channel_listing
                else None
            )
        )


class SaleCountableConnection(CountableConnection):
    class Meta:
        node = Sale


class VoucherChannelListing(CountableDjangoObjectType):
    class Meta:
        description = "Represents voucher channel listing."
        model = models.VoucherChannelListing
        interfaces = [graphene.relay.Node]
        only_fields = ["id", "channel", "discount_value", "currency", "min_spent"]

    @staticmethod
    def resolve_channel(root: models.VoucherChannelListing, info, **_kwargs):
        return ChannelByIdLoader(info.context).load(root.channel_id)


class Voucher(ChannelContextTypeWithMetadata, CountableDjangoObjectType):
    categories = ConnectionField(
        CategoryCountableConnection,
        description="List of categories this voucher applies to.",
    )
    collections = ConnectionField(
        CollectionCountableConnection,
        description="List of collections this voucher applies to.",
    )
    products = ConnectionField(
        ProductCountableConnection,
        description="List of products this voucher applies to.",
    )
    variants = ConnectionField(
        ProductVariantCountableConnection,
        description=f"{ADDED_IN_31} List of product variants this voucher applies to.",
    )
    countries = graphene.List(
        types.CountryDisplay,
        description="List of countries available for the shipping voucher.",
    )
    translation = TranslationField(
        VoucherTranslation,
        type_name="voucher",
        resolver=ChannelContextType.resolve_translation,
    )
    discount_value_type = DiscountValueTypeEnum(
        description="Determines a type of discount for voucher - value or percentage",
        required=True,
    )
    discount_value = graphene.Float(description="Voucher value.")
    currency = graphene.String(description="Currency code for voucher.")
    min_spent = graphene.Field(
        Money, description="Minimum order value to apply voucher."
    )
    type = VoucherTypeEnum(description="Determines a type of voucher.", required=True)
    channel_listings = graphene.List(
        graphene.NonNull(VoucherChannelListing),
        description="List of availability in channels for the voucher.",
    )

    class Meta:
        default_resolver = ChannelContextType.resolver_with_context
        description = (
            "Vouchers allow giving discounts to particular customers on categories, "
            "collections or specific products. They can be used during checkout by "
            "providing valid voucher codes."
        )
        only_fields = [
            "only_for_staff",
            "apply_once_per_order",
            "apply_once_per_customer",
            "code",
            "discount_value_type",
            "end_date",
            "id",
            "min_checkout_items_quantity",
            "name",
            "start_date",
            "type",
            "usage_limit",
            "used",
        ]
        interfaces = [relay.Node, ObjectWithMetadata]
        model = models.Voucher

    @staticmethod
    def resolve_categories(
        root: ChannelContext[models.Voucher], info, *_args, **kwargs
    ):
        qs = root.node.categories.all()
        return create_connection_slice(qs, info, kwargs, CategoryCountableConnection)

    @staticmethod
    @permission_required(DiscountPermissions.MANAGE_DISCOUNTS)
    def resolve_collections(
        root: ChannelContext[models.Voucher], info, *_args, **kwargs
    ):
        qs = root.node.collections.all()
        qs = ChannelQsContext(qs=qs, channel_slug=root.channel_slug)
        return create_connection_slice(qs, info, kwargs, CollectionCountableConnection)

    @staticmethod
    @permission_required(DiscountPermissions.MANAGE_DISCOUNTS)
    def resolve_products(root: ChannelContext[models.Voucher], info, **kwargs):
        qs = root.node.products.all()
        qs = ChannelQsContext(qs=qs, channel_slug=root.channel_slug)
        return create_connection_slice(qs, info, kwargs, ProductCountableConnection)

    @staticmethod
    @permission_required(DiscountPermissions.MANAGE_DISCOUNTS)
    def resolve_variants(root: ChannelContext[models.Voucher], info, **kwargs):
        qs = root.node.variants.all()
        qs = ChannelQsContext(qs=qs, channel_slug=root.channel_slug)
        return create_connection_slice(
            qs, info, kwargs, ProductVariantCountableConnection
        )

    @staticmethod
    def resolve_countries(root: ChannelContext[models.Voucher], *_args, **_kwargs):
        return [
            types.CountryDisplay(code=country.code, country=country.name)
            for country in root.node.countries
        ]

    @staticmethod
    def resolve_discount_value(root: ChannelContext[models.Voucher], info, **_kwargs):
        if not root.channel_slug:
            return None

        return (
            VoucherChannelListingByVoucherIdAndChanneSlugLoader(info.context)
            .load((root.node.id, root.channel_slug))
            .then(
                lambda channel_listing: channel_listing.discount_value
                if channel_listing
                else None
            )
        )

    @staticmethod
    def resolve_currency(root: ChannelContext[models.Voucher], info, **_kwargs):
        if not root.channel_slug:
            return None

        return (
            VoucherChannelListingByVoucherIdAndChanneSlugLoader(info.context)
            .load((root.node.id, root.channel_slug))
            .then(
                lambda channel_listing: channel_listing.currency
                if channel_listing
                else None
            )
        )

    @staticmethod
    def resolve_min_spent(root: ChannelContext[models.Voucher], info, **_kwargs):
        if not root.channel_slug:
            return None

        return (
            VoucherChannelListingByVoucherIdAndChanneSlugLoader(info.context)
            .load((root.node.id, root.channel_slug))
            .then(
                lambda channel_listing: channel_listing.min_spent
                if channel_listing
                else None
            )
        )

    @staticmethod
    @permission_required(DiscountPermissions.MANAGE_DISCOUNTS)
    def resolve_channel_listings(root: ChannelContext[models.Voucher], info, **_kwargs):
        return VoucherChannelListingByVoucherIdLoader(info.context).load(root.node.id)


class VoucherCountableConnection(CountableConnection):
    class Meta:
        node = Voucher


class OrderDiscount(CountableDjangoObjectType):
    value_type = graphene.Field(
        DiscountValueTypeEnum,
        required=True,
        description="Type of the discount: fixed or percent",
    )
    value = PositiveDecimal(
        required=True,
        description="Value of the discount. Can store fixed value or percent value",
    )
    reason = graphene.String(
        required=False, description="Explanation for the applied discount."
    )
    amount = graphene.Field(
        Money, description="Returns amount of discount.", required=True
    )

    class Meta:
        description = (
            "Contains all details related to the applied discount to the order."
        )
        only_fields = [
            "id",
            "type",
            "value",
            "value_type",
            "reason",
            "name",
            "translated_name",
        ]
        interfaces = [relay.Node]
        model = models.OrderDiscount

    @staticmethod
    @permission_required(OrderPermissions.MANAGE_ORDERS)
    def resolve_reason(root: models.OrderDiscount, _info):
        return root.reason
