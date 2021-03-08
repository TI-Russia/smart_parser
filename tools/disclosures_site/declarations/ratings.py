
class TPersonRatings:
    MaxDeclarantOfficeIncomeRating = 1
    MaxSpouseOfficeIncomeRating = 2
    LuxuryCarRating = 3

    @staticmethod
    def get_search_params_by_rating(rating):
        if rating.rating_id == TPersonRatings.MaxDeclarantOfficeIncomeRating:
            return "/section/?office_request={}&income_year={}&sort_by=income_size&order=desc".format(
                rating.office_id,
                rating.rating_year
                )
        elif rating.rating_id == TPersonRatings.MaxSpouseOfficeIncomeRating:
            return "/section/?office_request={}&income_year={}&sort_by=spouse_income_size&order=desc".format(
                rating.office_id,
                rating.rating_year
                )
        elif rating.rating_id == TPersonRatings.LuxuryCarRating:
            return "/section/?office_request={}&car_brands={}".format(
                rating.office_id,
                rating.rating_value
            )
        else:
            return ""