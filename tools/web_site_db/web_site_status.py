
class TWebSiteReachStatus:
    normal = "normal"
    only_selenium = "only_selenium"
    out_of_reach = "out_of_reach"   #nor urllib, neither selenium
    out_of_reach2 = "out_of_reach2" #we got out_of_reach at least two times
    abandoned = "abandoned"         #no trace in search engines

    @staticmethod
    def can_communicate(reach_status):
        return reach_status == TWebSiteReachStatus.normal or \
               reach_status == TWebSiteReachStatus.only_selenium

    @staticmethod
    def check_status(status):
        return status in {TWebSiteReachStatus.normal, TWebSiteReachStatus.only_selenium,
                           TWebSiteReachStatus.out_of_reach, TWebSiteReachStatus.abandoned,
                          TWebSiteReachStatus.out_of_reach2}
