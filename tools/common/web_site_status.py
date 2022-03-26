
class TWebSiteReachStatus:
    #"normal" means that dlrobot should fetch data from these sites in the standard (automatic) way
    normal = "normal"

    #Other statuses say that dlrobot should not fetch data from these sites
    #These sites can be outdated, abandoned or contain no declaration information
    out_of_reach = "out_of_reach"   #cannot load the main page in many tries
    abandoned = "abandoned"         #no trace in search engines or banned by hand
    unpromising = "unpromising" #website looks normal, but we cannot download a single declaration from this website

    @staticmethod
    def can_communicate(reach_status):
        return reach_status == TWebSiteReachStatus.normal

    @staticmethod
    def check_status(status):
        return status in {TWebSiteReachStatus.normal,
                           TWebSiteReachStatus.out_of_reach, TWebSiteReachStatus.abandoned,
                          TWebSiteReachStatus.unpromising
                          }
