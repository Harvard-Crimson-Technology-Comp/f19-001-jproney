import graphene
from project1.api.models import StockModel, PortfolioModel, UserModel, PurchaseModel
from graphene_django.types import DjangoObjectType


class StockType(DjangoObjectType):
    class Meta:
        model = StockModel


class PurchaseType(DjangoObjectType):
    class Meta:
        model = PurchaseModel


class UserType(DjangoObjectType):
    class Meta:
        model = UserModel


class PortfolioType(DjangoObjectType):
    class Meta:
        model = PortfolioModel


class Query(object):
    all_stocks = graphene.List(StockType)
    all_users = graphene.List(PurchaseType)
    all_purchases = graphene.List(UserType)
    all_portfolios = graphene.List(PortfolioType)

    def resolve_all_portfolios(self, info, **kwargs):
        return PortfolioType.objects.all()

    def resolve_all_stocks(self, info, **kwargs):
        return StockType.objects.all()

    def resolve_all_users(self, info, **kwargs):
        return UserType.objects.all()

    def resolve_all_purchases(self, info, **kwargs):
        return PurchaseType.objects.all()
