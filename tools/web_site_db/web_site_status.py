
class TWebSiteReachStatus:
    normal = "normal"
    out_of_reach = "out_of_reach"   #nor urllib, neither selenium
    abandoned = "abandoned"         #no trace in search engines

    @staticmethod
    def can_communicate(reach_status):
        return reach_status == TWebSiteReachStatus.normal

    @staticmethod
    def check_status(status):
        return status in {TWebSiteReachStatus.normal,
                           TWebSiteReachStatus.out_of_reach, TWebSiteReachStatus.abandoned
                          }
