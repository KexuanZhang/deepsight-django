from typing import Union, List
from urllib.parse import urlparse

import dspy

from ...interface import Retriever, Information
from ...utils import ArticleTextProcessing


# Internet source restrictions according to Wikipedia standard:
# https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources/Perennial_sources
SOURCE_CONFIGS = [
    {
        "Source": "112_Ukraine",
        "Status": "Generally unreliable",
        "Use": ["*.112.ua", "*.112.international"],
    },
    {
        "Source": "Acclaimed_Music",
        "Status": "Generally unreliable",
        "Use": ["*.acclaimedmusic.net"],
    },
    {
        "Source": "Ad_Fontes_Media",
        "Status": "Generally unreliable",
        "Use": ["*.adfontesmedia.com"],
    },
    {
        "Source": "Advameg",
        "Status": "Blacklisted",
        "Use": ["*.fundinguniverse.com", "*.company-histories.com"],
    },
    {
        "Source": "Al_Mayadeen",
        "Status": "Deprecated",
        "Use": ["*.almayadeen.net", "*.almayadeen.tv"],
    },
    {
        "Source": "Al-Manar_(controversial_topics)",
        "Status": "Generally unreliable",
        "Use": ["*.english.almanar.com.lb"],
    },
    {"Source": "AlterNet", "Status": "Generally unreliable", "Use": ["*.alternet.org"]},
    {
        "Source": "Amazon",
        "Status": "Generally unreliable",
        "Use": [
            "*.amazon.co.jp",
            "*.amazon.ca",
            "*.amazon.com.sg",
            "*.amazon.com.tr",
            "*.amazon.de",
            "*.amazon.com",
            "*.amazon.com.mx",
            "*.amazon.cn",
            "*.amazon.it",
            "*.amazon.com.br",
            "*.amazon.in",
            "*.amazon.co.uk",
            "*.amazon.es",
            "*.amazon.fr",
            "*.amazon.nl",
            "*.amazon.com.au",
        ],
    },
    {
        "Source": "Anadolu_Agency_(controversial_topics)",
        "Status": "Generally unreliable",
        "Use": ["*.aa.com.tr", "*.aa.com.tr\/en"],
    },
    {
        "Source": "Ancestry.com",
        "Status": "Generally unreliable",
        "Use": ["*.ancestry.com"],
    },
    {"Source": "ANNA_News", "Status": "Deprecated", "Use": ["*.anna-news.info"]},
    {
        "Source": "Answers.com",
        "Status": "Generally unreliable",
        "Use": ["*.answers.com"],
    },
    {
        "Source": "Anti-Defamation_League_(Israel\/Palestine_conflict)",
        "Status": "Generally unreliable",
        "Use": ["*.adl.org"],
    },
    {
        "Source": "Antiwar.com",
        "Status": "Generally unreliable",
        "Use": ["*.antiwar.org", "*.antiwar.com"],
    },
    {
        "Source": "Army_Recognition",
        "Status": "Generally unreliable",
        "Use": ["*.armyrecognition.com", "*.navyrecognition.com"],
    },
    {
        "Source": "Atlas_Obscura_places",
        "Status": "Generally unreliable",
        "Use": ["*.atlasobscura.com\/places"],
    },
    {
        "Source": "Baidu_Baike",
        "Status": "Deprecated",
        "Use": [
            "*.wapbaike.baidu.com",
            "*.baike.baidu.hk",
            "*.baike.baidu.com",
            "*.b.baidu.com",
        ],
    },
    {"Source": "bestgore.com", "Status": "Blacklisted", "Use": ["*.bestgore.com"]},
    {"Source": "Bild", "Status": "Generally unreliable", "Use": ["*.bild.de"]},
    {
        "Source": "Blaze_Media",
        "Status": "Generally unreliable",
        "Use": ["*.conservativereview.com", "*.theblaze.com"],
    },
    {"Source": "Blogger", "Status": "Generally unreliable", "Use": ["*.blogspot.com"]},
    {
        "Source": "Breitbart_News",
        "Status": "Blacklisted",
        "Use": ["*.breitbart.com", "*.biggovernment.com"],
    },
    {
        "Source": "BroadwayWorld",
        "Status": "Generally unreliable",
        "Use": ["*.broadwayworld.com"],
    },
    {
        "Source": "The_California_Globe",
        "Status": "Generally unreliable",
        "Use": ["*.californiaglobe.com\/"],
    },
    {
        "Source": "The_Canary",
        "Status": "Generally unreliable",
        "Use": ["*.thecanary.co"],
    },
    {
        "Source": "Catholic-Hierarchy.org",
        "Status": "Generally unreliable",
        "Use": ["*.catholic-hierarchy.org"],
    },
    {
        "Source": "CelebrityNetWorth",
        "Status": "Generally unreliable",
        "Use": ["*.celebritynetworth.com"],
    },
    {
        "Source": "Centre_for_Research_on_Globalization",
        "Status": "Blacklisted",
        "Use": ["*.mondialisation.ca", "*.globalresearch.org", "*.globalresearch.ca"],
    },
    {
        "Source": "CESNUR",
        "Status": "Generally unreliable",
        "Use": ["*.bitterwinter.org", "*.cesnur.net", "*.cesnur.org"],
    },
    {"Source": "Change.org", "Status": "Blacklisted", "Use": ["*.change.org"]},
    {
        "Source": "China_Global_Television_Network",
        "Status": "Deprecated",
        "Use": ["*.cgtn.com"],
    },
    {
        "Source": "CNET_(October_2020\u2013October_2022)",
        "Status": "Generally unreliable",
        "Use": ["*.cnet.com"],
    },
    {
        "Source": "CNET_(November_2022\u2013present)",
        "Status": "Generally unreliable",
        "Use": ["*.cnet.com"],
    },
    {"Source": "CoinDesk", "Status": "Generally unreliable", "Use": ["*.coindesk.com"]},
    {
        "Source": "Consortium_News",
        "Status": "Generally unreliable",
        "Use": ["*.consortiumnews.com"],
    },
    {
        "Source": "Correo_del_Orinoco",
        "Status": "Generally unreliable",
        "Use": ["*.correodelorinoco.gob.ve"],
    },
    {
        "Source": "CounterPunch",
        "Status": "Generally unreliable",
        "Use": ["*.counterpunch.com", "*.counterpunch.org"],
    },
    {
        "Source": "Cracked.com",
        "Status": "Generally unreliable",
        "Use": ["*.cracked.com"],
    },
    {"Source": "The_Cradle", "Status": "Deprecated", "Use": ["*.thecradle.co"]},
    {"Source": "Crunchbase", "Status": "Deprecated", "Use": ["*.crunchbase.com"]},
    {
        "Source": "The_Daily_Caller",
        "Status": "Deprecated",
        "Use": ["*.dailycallernewsfoundation.org", "*.dailycaller.com"],
    },
    {
        "Source": "Daily_Express",
        "Status": "Generally unreliable",
        "Use": ["*.express.co.uk", "*.pressreader.com\/uk\/daily-express"],
    },
    {
        "Source": "Daily_Kos",
        "Status": "Generally unreliable",
        "Use": ["*.dailykos.com"],
    },
    {
        "Source": "Daily_Mail",
        "Status": "Deprecated",
        "Use": [
            "*.mailpictures.newsprints.co.uk",
            "*.pressreader.com\/ireland\/irish-daily-mail",
            "*.dailymail.com.au",
            "*.dailymail.com",
            "*.findarticles.com\/p\/news-articles\/daily-mail-london-england-the\/",
            "*.pressreader.com\/uk\/daily-mail",
            "*.dailymail.co.uk",
            "*.dailym.ai",
            "*.mailonline.pressreader.com",
            "*.mailplus.co.uk",
            "*.thisismoney.co.uk",
            "*.travelmail.co.uk",
            "*.pressreader.com\/uk\/scottish-daily-mail",
        ],
    },
    {
        "Source": "Daily_Sabah",
        "Status": "Generally unreliable",
        "Use": ["*.dailysabah.com"],
    },
    {
        "Source": "Daily_Star",
        "Status": "Deprecated",
        "Use": ["*.dailystar.co.uk", "*.thestar.ie"],
    },
    {
        "Source": "The_Daily_Wire",
        "Status": "Generally unreliable",
        "Use": ["*.dailywire.com"],
    },
    {"Source": "Discogs", "Status": "Generally unreliable", "Use": ["*.discogs.com"]},
    {
        "Source": "Distractify",
        "Status": "Generally unreliable",
        "Use": ["*.distractify.com"],
    },
    {
        "Source": "The_Dorchester_Review",
        "Status": "Generally unreliable",
        "Use": ["*.dorchesterreview.ca"],
    },
    {"Source": "EADaily", "Status": "Deprecated", "Use": ["*.eadaily.com"]},
    {
        "Source": "The_Electronic_Intifada",
        "Status": "Generally unreliable",
        "Use": ["*.electronicintifada.net"],
    },
    {
        "Source": "Encyclopaedia_Metallum",
        "Status": "Generally unreliable",
        "Use": ["*.metal-archives.com"],
    },
    {
        "Source": "The_Epoch_Times",
        "Status": "Deprecated",
        "Use": [
            "*.theepochtimes.com",
            "*.visiontimes.fr",
            "*.ntdtv.com.tw",
            "*.epochtimes.de",
            "*.epochtimes.fr",
            "*.secretchina.com",
            "*.epochtimes.it",
            "*.epochtimes.se",
            "*.ntdtv.com",
            "*.epochtimes.co.il",
            "*.vibrantdot.co",
            "*.epochtimes.co.kr",
            "*.visiontimes.com.au",
            "*.ntd.com",
            "*.epoch.org.il",
            "*.visiontimes.com",
            "*.epochtimes.com",
            "*.epochtimes.cz",
            "*.ntdtv.ca",
            "*.epochtimes.ru",
            "*.epochtimes-romania.com",
            "*.epoch-archive.com",
            "*.visiontimesjp.com",
            "*.nspirement.com",
            "*.trithucvn.net",
        ],
    },
    {
        "Source": "Ethnicity_of_Celebs",
        "Status": "Generally unreliable",
        "Use": ["*.ethnicelebs.com"],
    },
    {
        "Source": "The_EurAsian_Times",
        "Status": "Generally unreliable",
        "Use": ["*.eurasiantimes.com"],
    },
    {"Source": "Examiner.com", "Status": "Blacklisted", "Use": ["*.examiner.com"]},
    {"Source": "Facebook", "Status": "Generally unreliable", "Use": ["*.facebook.com"]},
    {
        "Source": "FamilySearch",
        "Status": "Generally unreliable",
        "Use": ["*.familysearch.org"],
    },
    {
        "Source": "Famous_Birthdays",
        "Status": "Blacklisted",
        "Use": ["*.famousbirthdays.com"],
    },
    {
        "Source": "Fandom",
        "Status": "Generally unreliable",
        "Use": ["*.wikia.com", "*.wikicities.com", "*.wikia.org", "*.fandom.com"],
    },
    {
        "Source": "The_Federalist",
        "Status": "Generally unreliable",
        "Use": ["*.thefederalist.com"],
    },
    {
        "Source": "FilmAffinity",
        "Status": "Generally unreliable",
        "Use": ["*.filmaffinity.com"],
    },
    {
        "Source": "Find_a_Grave",
        "Status": "Generally unreliable",
        "Use": ["*.findagrave.com"],
    },
    {
        "Source": "Findmypast",
        "Status": "Generally unreliable",
        "Use": ["*.findmypast.co.uk", "*.findmypast.com"],
    },
    {
        "Source": "Flags_of_the_World",
        "Status": "Generally unreliable",
        "Use": ["*.fotw.info", "*.crwflags.com\/fotw"],
    },
    {"Source": "Flickr", "Status": "Generally unreliable", "Use": ["*.flickr.com"]},
    {
        "Source": "Forbes.com_contributors",
        "Status": "Generally unreliable",
        "Use": ["*.forbes.com"],
    },
    {
        "Source": "Forbes_Advisor",
        "Status": "Generally unreliable",
        "Use": ["*.forbes.com\/advisor"],
    },
    {
        "Source": "Fox_News_(politics_and_science)",
        "Status": "Generally unreliable",
        "Use": ["*.foxnews.com"],
    },
    {
        "Source": "Fox_News_(talk_shows)",
        "Status": "Generally unreliable",
        "Use": ["*.foxnews.com"],
    },
    {
        "Source": "FrontPage_Magazine",
        "Status": "Deprecated",
        "Use": ["*.frontpagemagazine.com", "*.frontpagemag.com"],
    },
    {
        "Source": "The_Gateway_Pundit",
        "Status": "Deprecated",
        "Use": ["*.thegatewaypundit.com"],
    },
    {"Source": "Gawker", "Status": "Generally unreliable", "Use": ["*.gawker.com"]},
    {
        "Source": "GB_News",
        "Status": "Generally unreliable",
        "Use": ["*.gbnews.uk", "*.gbnews.com"],
    },
    {
        "Source": "Genealogy.eu",
        "Status": "Deprecated",
        "Use": ["*.genealogy.eu", "*.genealogy.euweb.cz"],
    },
    {"Source": "Geni.com", "Status": "Deprecated", "Use": ["*.geni.com"]},
    {
        "Source": "gnis-class",
        "Status": "Generally unreliable",
        "Use": ["*.geonames.usgs.gov"],
    },
    {
        "Source": "gns-class",
        "Status": "Generally unreliable",
        "Use": ["*.geonames.nga.mil"],
    },
    {
        "Source": "Global_Times",
        "Status": "Deprecated",
        "Use": ["*.globaltimes.cn", "*.huanqiu.com"],
    },
    {
        "Source": "GlobalSecurity.org",
        "Status": "Generally unreliable",
        "Use": ["*.globalsecurity.org"],
    },
    {
        "Source": "GoFundMe",
        "Status": "Blacklisted",
        "Use": ["*.youcaring.com", "*.gofundme.com"],
    },
    {
        "Source": "Goodreads",
        "Status": "Generally unreliable",
        "Use": ["*.goodreads.com"],
    },
    {"Source": "The_Grayzone", "Status": "Deprecated", "Use": ["*.thegrayzone.com"]},
    {
        "Source": "Guido_Fawkes",
        "Status": "Generally unreliable",
        "Use": ["*.order-order.com"],
    },
    {"Source": "Healthline", "Status": "Blacklisted", "Use": ["*.healthline.com"]},
    {
        "Source": "Heat_Street",
        "Status": "Generally unreliable",
        "Use": ["*.heatst.com"],
    },
    {
        "Source": "The_Heritage_Foundation",
        "Status": "Blacklisted",
        "Use": ["*.heritage.org"],
    },
    {
        "Source": "HispanTV",
        "Status": "Deprecated",
        "Use": ["*.hispantv.ir", "*.hispantv.com"],
    },
    {"Source": "History", "Status": "Generally unreliable", "Use": ["*.history.com"]},
    {
        "Source": "HuffPost_contributors",
        "Status": "Generally unreliable",
        "Use": ["*.huffpost.com", "*.huffingtonpost.com"],
    },
    {"Source": "IMDb", "Status": "Generally unreliable", "Use": ["*.imdb.com"]},
    {
        "Source": "Independent_Media_Center",
        "Status": "Generally unreliable",
        "Use": [
            "*.phillyimc.org",
            "*.indymedia.us",
            "*.midiaindependente.org",
            "*.tnimc.org",
            "*.indymediapr.org",
            "*.indymedia.org.uk",
            "*.bigmuddyimc.org",
            "*.indymedia.no",
            "*.antwerpen-indymedia.be",
            "*.indymedia.org",
            "*.indymedia.nl",
            "*.rogueimc.org",
            "*.indymedia.ie",
            "*.imc-africa.mayfirst.org",
            "*.michiganimc.org",
            "*.ucimc.org",
            "*.indybay.org",
        ],
    },
    {"Source": "Indiegogo", "Status": "Blacklisted", "Use": ["*.indiegogo.com"]},
    {
        "Source": "Infowars",
        "Status": "Blacklisted",
        "Use": [
            "*.newswars.com",
            "*.nationalfile.com",
            "*.banned.video",
            "*.infowars.com",
            "*.infowars.tv",
            "*.infowars.net",
        ],
    },
    {
        "Source": "Inquisitr",
        "Status": "Generally unreliable",
        "Use": ["*.inquisitr.com"],
    },
    {
        "Source": "Instagram",
        "Status": "Generally unreliable",
        "Use": ["*.instagram.com"],
    },
    {
        "Source": "International_Business_Times",
        "Status": "Generally unreliable",
        "Use": [
            "*.ibtimes.co.uk",
            "*.ibtimes.com.cn",
            "*.ibtimes.co.in",
            "*.ibtimes.sg",
            "*.ibtimes.com",
            "*.ibtimes.com.au",
        ],
    },
    {
        "Source": "Investopedia",
        "Status": "Generally unreliable",
        "Use": ["*.investopedia.com"],
    },
    {
        "Source": "Jewish_Virtual_Library",
        "Status": "Generally unreliable",
        "Use": ["*.jewishvirtuallibrary.org"],
    },
    {"Source": "Jihad_Watch", "Status": "Deprecated", "Use": ["*.jihadwatch.org"]},
    {
        "Source": "Joshua_Project",
        "Status": "Generally unreliable",
        "Use": ["*.religjournal.com\/pdf\/ijrr11010.pdf", "*.joshuaproject.net"],
    },
    {"Source": "Kickstarter", "Status": "Blacklisted", "Use": ["*.kickstarter.com"]},
    {
        "Source": "Know_Your_Meme",
        "Status": "Generally unreliable",
        "Use": ["*.knowyourmeme.com"],
    },
    {
        "Source": "Kotaku_(2023\u2013present)",
        "Status": "Generally unreliable",
        "Use": ["*.kotaku.co.uk", "*.kotaku.com", "*.kotaku.com.au"],
    },
    {
        "Source": "Land_Transport_Guru",
        "Status": "Generally unreliable",
        "Use": ["*.landtransportguru.net"],
    },
    {"Source": "Last.fm", "Status": "Deprecated", "Use": ["*.last.fm"]},
    {"Source": "Lenta.ru", "Status": "Blacklisted", "Use": ["*.lenta.ru"]},
    {
        "Source": "LifeSiteNews",
        "Status": "Deprecated",
        "Use": ["*.lifesite.net", "*.lifesitenews.com"],
    },
    {"Source": "LinkedIn", "Status": "Generally unreliable", "Use": ["*.linkedin.com"]},
    {
        "Source": "LionhearTV",
        "Status": "Generally unreliable",
        "Use": ["*.lionheartv.net"],
    },
    {
        "Source": "LiveJournal",
        "Status": "Generally unreliable",
        "Use": ["*.livejournal.com"],
    },
    {"Source": "LiveLeak", "Status": "Blacklisted", "Use": ["*.liveleak.com"]},
    {"Source": "Lulu.com", "Status": "Blacklisted", "Use": ["*.lulu.com"]},
    {
        "Source": "The_Mail_on_Sunday",
        "Status": "Deprecated",
        "Use": [
            "*.dailymail.co.uk\/mailonsunday",
            "*.pressreader.com\/uk\/the-scottish-mail-on-sunday\/",
            "*.mailonsunday.co.uk",
            "*.pressreader.com\/uk\/the-mail-on-sunday\/",
        ],
    },
    {
        "Source": "Marquis_Who's_Who",
        "Status": "Generally unreliable",
        "Use": ["*.whoswhoinamerica.com", "*.marquiswhoswho.com"],
    },
    {
        "Source": "Mashable_sponsored_content",
        "Status": "Generally unreliable",
        "Use": ["*.mashable.com"],
    },
    {"Source": "MEAWW", "Status": "Generally unreliable", "Use": ["*.meaww.com"]},
    {
        "Source": "Media_Bias\/Fact_Check",
        "Status": "Generally unreliable",
        "Use": ["*.mediabiasfactcheck.com"],
    },
    {
        "Source": "Media_Research_Center",
        "Status": "Generally unreliable",
        "Use": ["*.newsbusters.org", "*.cnsnews.com", "*.mrctv.org", "*.mrc.org"],
    },
    {"Source": "Medium", "Status": "Generally unreliable", "Use": ["*.medium.com"]},
    {
        "Source": "metal-experience",
        "Status": "Generally unreliable",
        "Use": ["*.metal-experience.com"],
    },
    {
        "Source": "Metro",
        "Status": "Generally unreliable",
        "Use": ["*.metro.co.uk", "*.metro.news"],
    },
    {
        "Source": "MintPress_News",
        "Status": "Deprecated",
        "Use": [
            "*.mintpressnews.com",
            "*.mintpressnews.ru",
            "*.mintpressnews.es",
            "*.mintpressnews.cn",
        ],
    },
    {
        "Source": "MyLife",
        "Status": "Blacklisted",
        "Use": ["*.mylife.com", "*.reunion.com"],
    },
    {
        "Source": "National_Enquirer",
        "Status": "Deprecated",
        "Use": ["*.nationalenquirer.com"],
    },
    {
        "Source": "Natural_News",
        "Status": "Blacklisted",
        "Use": [
            "*.naturalnews.com",
            "www.isdglobal.org\/isd-publications\/investigating-natural-news\/",
            "*.newstarget.com",
        ],
    },
    {
        "Source": "The_New_American",
        "Status": "Generally unreliable",
        "Use": ["*.thenewamerican.com"],
    },
    {
        "Source": "New_Eastern_Outlook",
        "Status": "Deprecated",
        "Use": ["*.journal-neo.org"],
    },
    {
        "Source": "New_York_Post",
        "Status": "Generally unreliable",
        "Use": ["*.nypost.com", "*.pagesix.com"],
    },
    {
        "Source": "News_of_the_World",
        "Status": "Deprecated",
        "Use": ["*.newsoftheworld.com", "*.newsoftheworld.co.uk"],
    },
    {
        "Source": "NewsBlaze",
        "Status": "Deprecated",
        "Use": ["*.newsblaze.com", "*.newsblaze.com.au"],
    },
    {"Source": "NewsBreak", "Status": "Deprecated", "Use": ["*.newsbreak.com"]},
    {"Source": "NewsFront", "Status": "Blacklisted", "Use": ["*.newsfront.info"]},
    {
        "Source": "Newsmax",
        "Status": "Deprecated",
        "Use": ["*.newsmaxtv.com", "*.newsmax.com"],
    },
    {
        "Source": "NewsNation",
        "Status": "Generally unreliable",
        "Use": ["*.newsnationnow.com"],
    },
    {
        "Source": "NGO_Monitor",
        "Status": "Generally unreliable",
        "Use": ["*.ngo-monitor.org"],
    },
    {"Source": "NNDB", "Status": "Deprecated", "Use": ["*.nndb.com"]},
    {
        "Source": "Occupy_Democrats",
        "Status": "Deprecated",
        "Use": ["*.washingtonpress.com", "*.occupydemocrats.com"],
    },
    {
        "Source": "Office_of_Cuba_Broadcasting",
        "Status": "Deprecated",
        "Use": ["*.martinoticias.com"],
    },
    {
        "Source": "One_America_News_Network",
        "Status": "Deprecated",
        "Use": ["*.oann.com"],
    },
    {
        "Source": "The_Onion",
        "Status": "Generally unreliable",
        "Use": ["*.theonion.com"],
    },
    {
        "Source": "OpIndia",
        "Status": "Blacklisted",
        "Use": ["*.opindia.in", "*.opindia.com"],
    },
    {
        "Source": "Our_Campaigns",
        "Status": "Generally unreliable",
        "Use": ["*.ourcampaigns.com"],
    },
    {
        "Source": "PanAm_Post",
        "Status": "Generally unreliable",
        "Use": ["*.panampost.com"],
    },
    {"Source": "Patheos", "Status": "Generally unreliable", "Use": ["*.patheos.com"]},
    {
        "Source": "Peerage_websites",
        "Status": "Deprecated",
        "Use": ["#Self-published_peerage_websites"],
    },
    {
        "Source": "An_Phoblacht",
        "Status": "Generally unreliable",
        "Use": ["*.anphoblacht.com"],
    },
    {
        "Source": "Planespotters",
        "Status": "Generally unreliable",
        "Use": ["*.planespotters.net"],
    },
    {
        "Source": "The_Points_Guy",
        "Status": "Blacklisted",
        "Use": ["*.thepointsguy.com\/reviews", "*.thepointsguy.com\/news"],
    },
    {
        "Source": "The_Points_Guy_(sponsored_content)",
        "Status": "Blacklisted",
        "Use": ["*.thepointsguy.com"],
    },
    {
        "Source": "The_Post_Millennial",
        "Status": "Generally unreliable",
        "Use": ["*.thepostmillennial.com"],
    },
    {
        "Source": "PR_Newswire",
        "Status": "Generally unreliable",
        "Use": ["*.prnewswire.com", "*.prnewswire.co.uk"],
    },
    {
        "Source": "Press_TV",
        "Status": "Deprecated",
        "Use": ["*.presstv.co.uk", "*.presstv.tv", "*.presstv.com", "*.presstv.ir"],
    },
    {
        "Source": "Project_Veritas",
        "Status": "Blacklisted",
        "Use": ["*.okeefemediagroup.com", "*.projectveritas.com"],
    },
    {
        "Source": "Quadrant",
        "Status": "Generally unreliable",
        "Use": ["*.quadrant.org.au"],
    },
    {
        "Source": "Quillette",
        "Status": "Generally unreliable",
        "Use": ["*.quillette.com"],
    },
    {"Source": "Quora", "Status": "Generally unreliable", "Use": ["*.quora.com"]},
    {
        "Source": "Rate_Your_Music",
        "Status": "Deprecated",
        "Use": [
            "*.glitchwave.com",
            "*.cinemos.com",
            "*.rateyourmusic.com",
            "*.sonemic.com",
        ],
    },
    {
        "Source": "Raw_Story",
        "Status": "Generally unreliable",
        "Use": ["*.rawstory.com"],
    },
    {"Source": "Red_Ventures", "Status": "Generally unreliable", "Use": []},
    {"Source": "RedState", "Status": "Generally unreliable", "Use": ["*.redstate.com"]},
    {
        "Source": "Republic_TV",
        "Status": "Deprecated",
        "Use": ["*.bharat.republicworld.com", "*.republicworld.com"],
    },
    {
        "Source": "Rolling_Stone_(politics_and_society,_2011\u2013present)",
        "Status": "Generally unreliable",
        "Use": ["*.rollingstone.com\/politics"],
    },
    {
        "Source": "Rolling_Stone_(Culture_Council)",
        "Status": "Generally unreliable",
        "Use": ["*.council.rollingstone.com", "*.rollingstone.com\/culture-council"],
    },
    {
        "Source": "Royal_Central",
        "Status": "Deprecated",
        "Use": ["*.royalcentral.co.uk"],
    },
    {
        "Source": "RT",
        "Status": "Deprecated",
        "Use": [
            "*.russiatoday.com",
            "*.actualidad-rt.com",
            "*.rt.com",
            "*.redfish.media",
            "*.rt.rs",
            "*.russiatoday.ru",
            "*.ruptly.tv",
        ],
    },
    {
        "Source": "ScienceDirect_topic",
        "Status": "Generally unreliable",
        "Use": ["*.sciencedirect.com\/topics\/"],
    },
    {"Source": "Scribd", "Status": "Generally unreliable", "Use": ["*.scribd.com"]},
    {"Source": "Scriptural_texts", "Status": "Generally unreliable", "Use": []},
    {
        "Source": "Simple_Flying",
        "Status": "Generally unreliable",
        "Use": ["*.simpleflying.com"],
    },
    {
        "Source": "Sixth_Tone_(politics)",
        "Status": "Generally unreliable",
        "Use": ["*.sixthtone.com"],
    },
    {
        "Source": "The_Skwawkbox",
        "Status": "Generally unreliable",
        "Use": ["*.skwawkbox.org"],
    },
    {
        "Source": "SourceWatch",
        "Status": "Generally unreliable",
        "Use": ["*.sourcewatch.org"],
    },
    {
        "Source": "SouthFront",
        "Status": "Blacklisted",
        "Use": ["*.southfront.press", "*.southfront.org"],
    },
    {
        "Source": "Spirit_of_Metal",
        "Status": "Generally unreliable",
        "Use": ["*.spirit-of-metal.com"],
    },
    {
        "Source": "Sportskeeda",
        "Status": "Generally unreliable",
        "Use": ["*.sportskeeda.com"],
    },
    {
        "Source": "Sputnik",
        "Status": "Deprecated",
        "Use": [
            "*.sputniknews.lt",
            "*.sputnikportal.rs",
            "*.sputniknews.gr",
            "*.sputnik.kz",
            "*.sputnik.md",
            "*.sputniknews-uz.com",
            "*.sputnik.kg",
            "*.sputnikglobe.com",
            "*.sputniknews.africa",
            "*.sputniknews.com",
            "*.sputnik-ossetia.com",
            "*.sputnik-tj.com",
            "*.sputniknews.in",
            "*.latamnews.lat",
            "*.sputnik-abkhazia.info",
            "*.sputniknewslv.com",
            "*.voiceofrussia.com",
            "*.sputniknews.ru",
            "*.sputnik-ossetia.ru",
            "*.sputnik-abkhazia.ru",
            "*.armeniasputnik.am",
            "*.sarabic.ae",
            "*.sputnik.by",
            "*.radiosputnik.ria.ru",
            "*.sputnik-georgia.com",
            "*.sputnikmediabank.com",
            "*.sputniknews.cn",
            "*.sputniknews.lat",
            "*.sputnik.az",
            "*.sputnik-georgia.ru",
            "*.sputniknews.uz",
        ],
    },
    {
        "Source": "Stack_Exchange",
        "Status": "Generally unreliable",
        "Use": [
            "*.superuser.com",
            "*.stackoverflow.com",
            "*.askubuntu.com",
            "*.serverfault.com",
            "*.stackexchange.com",
            "*.mathoverflow.net",
        ],
    },
    {
        "Source": "starsunfolded.com",
        "Status": "Generally unreliable",
        "Use": ["*.starsunfolded.com"],
    },
    {"Source": "Statista", "Status": "Generally unreliable", "Use": ["*.statista.com"]},
    {
        "Source": "The_Sun",
        "Status": "Deprecated",
        "Use": [
            "*.thesun.co.uk",
            "*.thescottishsun.co.uk",
            "*.sunnation.co.uk",
            "*.dreamteamfc.com",
            "*.thesun.ie",
            "*.thesun.mobi",
            "*.page3.com",
            "*.the-sun.com",
        ],
    },
    {"Source": "Swarajya", "Status": "Blacklisted", "Use": ["*.swarajyamag.com"]},
    {"Source": "Taki's_Magazine", "Status": "Deprecated", "Use": ["*.takimag.com"]},
    {
        "Source": "Tasnim_News_Agency",
        "Status": "Deprecated",
        "Use": ["*.tasnimnews.com"],
    },
    {
        "Source": "TASS",
        "Status": "Generally unreliable",
        "Use": ["*.tass.ru", "*.tass.com"],
    },
    {
        "Source": "Telesur",
        "Status": "Deprecated",
        "Use": ["*.telesurtv.net", "*.telesurenglish.net"],
    },
    {
        "Source": "Town_and_Village_Guide_(UK)",
        "Status": "Generally unreliable",
        "Use": ["*.townandvillageguide.com"],
    },
    {
        "Source": "The_Truth_About_Guns",
        "Status": "Generally unreliable",
        "Use": ["*.thetruthaboutguns.com"],
    },
    {"Source": "TV.com", "Status": "Generally unreliable", "Use": ["*.TV.com"]},
    {
        "Source": "TV_Tropes",
        "Status": "Generally unreliable",
        "Use": ["*.tvtropes.org"],
    },
    {
        "Source": "The_Unz_Review",
        "Status": "Deprecated",
        "Use": ["*.unz.com", "*.unz.org"],
    },
    {
        "Source": "Urban_Dictionary",
        "Status": "Generally unreliable",
        "Use": ["*.urbandictionary.com"],
    },
    {"Source": "VDARE", "Status": "Deprecated", "Use": ["*.vdare.com"]},
    {
        "Source": "Venezuelanalysis",
        "Status": "Generally unreliable",
        "Use": ["*.venezuelanalysis.com"],
    },
    {
        "Source": "Veterans_Today",
        "Status": "Blacklisted",
        "Use": ["*.vtforeignpolicy.com", "*.veteranstoday.com"],
    },
    {"Source": "VGChartz", "Status": "Generally unreliable", "Use": ["*.vgchartz.com"]},
    {
        "Source": "VoC",
        "Status": "Generally unreliable",
        "Use": ["*.victimsofcommunism.org"],
    },
    {
        "Source": "Voltaire_Network",
        "Status": "Deprecated",
        "Use": ["*.voltairenet.org"],
    },
    {
        "Source": "Washington_Free_Beacon",
        "Status": "Generally unreliable",
        "Use": ["*.freebeacon.com"],
    },
    {
        "Source": "WatchMojo",
        "Status": "Generally unreliable",
        "Use": ["*.watchmojo.com"],
    },
    {
        "Source": "Weather2Travel",
        "Status": "Generally unreliable",
        "Use": ["*.weather2travel.com"],
    },
    {
        "Source": "The_Western_Journal",
        "Status": "Generally unreliable",
        "Use": ["*.westernjournal.com"],
    },
    {
        "Source": "We_Got_This_Covered",
        "Status": "Generally unreliable",
        "Use": ["*.wegotthiscovered.com"],
    },
    {"Source": "Wen_Wei_Po", "Status": "Deprecated", "Use": ["*.wenweipo.com"]},
    {
        "Source": "WhatCulture",
        "Status": "Generally unreliable",
        "Use": ["*.whatculture.com"],
    },
    {
        "Source": "Who's_Who_(UK)",
        "Status": "Generally unreliable",
        "Use": ["*.ukwhoswho.com"],
    },
    {
        "Source": "WhoSampled",
        "Status": "Generally unreliable",
        "Use": ["*.whosampled.com"],
    },
    {"Source": "Wikidata", "Status": "Generally unreliable", "Use": ["*.wikidata.org"]},
    {
        "Source": "WikiLeaks",
        "Status": "Generally unreliable",
        "Use": ["*.wikileaks.org"],
    },
    {"Source": "Wikinews", "Status": "Generally unreliable", "Use": ["*.wikinews.org"]},
    {
        "Source": "Wikipedia",
        "Status": "Generally unreliable",
        "Use": ["*.wikipedia.org"],
    },
    {
        "Source": "WordPress.com",
        "Status": "Generally unreliable",
        "Use": ["*.wordpress.com"],
    },
    {
        "Source": "WorldNetDaily",
        "Status": "Deprecated",
        "Use": ["*.wnd.com", "*.worldnetdaily.com"],
    },
    {
        "Source": "Worldometer",
        "Status": "Generally unreliable",
        "Use": ["*.worldometers.info"],
    },
    {"Source": "YouTube", "Status": "Generally unreliable", "Use": ["*.youtube.com"]},
    {
        "Source": "ZDNet_(October_2020\u2013present)",
        "Status": "Generally unreliable",
        "Use": ["*.zdnet.com"],
    },
    {"Source": "Zero_Hedge", "Status": "Deprecated", "Use": ["*.zerohedge.com"]},
    {"Source": "ZoomInfo", "Status": "Blacklisted", "Use": ["*.zoominfo.com"]},
]

GENERALLY_UNRELIABLE = set()
DEPRECATED = set()
BLACKLISTED = set()
for entry in SOURCE_CONFIGS:
    status = entry.get("Status", "").lower()
    for pattern in entry.get("Use", []):
        if status == "generally unreliable":
            GENERALLY_UNRELIABLE.add(pattern)
        elif status == "deprecated":
            DEPRECATED.add(pattern)
        elif status == "blacklisted":
            BLACKLISTED.add(pattern)


WHITELISTED_DOMAINS = [
    "https://arxiv.org",
    "https://paperswithcode.com",
    "https://semanticscholar.org",
    "https://scholar.google.com",
    "https://huggingface.co/papers",
    "https://paperdigest.org",
    "https://researchgate.net",
    "https://consensus.app",
    "https://scispace.com",
    "https://openreview.net",
    "https://dblp.org",
    "https://ssrn.com",
    "https://core.ac.uk",
    "https://journals.plos.org/plosone",
    "https://ieeexplore.ieee.org",
    "https://springer.com/journal/10994",
    "https://jmlr.org",
    "https://nature.com/natmachintell",
    "https://www.deepmind.com",
    "https://ai.google",
    "https://ai.meta.com",
    "https://www.microsoft.com/en-us/research",
    "https://research.ibm.com",
    "https://www.amazon.science",
    "https://www.alibaba.com/ai",
    "https://www.sensetime.com/en",
    "https://www.megvii.com/en",
    "https://www.iflytek.com/en",
    "https://www.clarifai.com/blog",
    "https://www.datarobot.com/blog",
    "https://www.technologyreview.com/artificial-intelligence",
    "https://www.wired.com/tag/artificial-intelligence",
    "https://techcrunch.com/category/artificial-intelligence",
    "https://www.kdnuggets.com",
    "https://tldr.tech/ai",
    "https://syncedreview.com",
    "https://www.analyticsvidhya.com",
    "https://thenextweb.com/neural",
    "https://arstechnica.com/information-technology",
    "https://distill.pub",
    "https://ai.googleblog.com",
    "https://openai.com/blog",
    "https://bair.berkeley.edu/blog",
    "https://news.mit.edu/topic/artificial-intelligence2",
    "https://becominghuman.ai",
    "https://chatbotslife.com",
    "https://www.artificiallawyer.com",
    "https://www.unite.ai",
    "https://www.marktechpost.com",
    "https://buzzrobot.com",
    "https://dair-ai.github.io",
    "https://gitlab.com/explore/projects/topics/ai",
    "https://www.fast.ai",
    "https://machinelearningmastery.com",
    "https://towardsdatascience.com",
    "https://datatalks.club",
    "https://ai.stackexchange.com",
    "https://datascience.stackexchange.com",
    "https://stackoverflow.com/questions/tagged/machine-learning",
    "https://oecd.ai",
    "https://www.gov.uk/government/groups/ai-council",
    "https://www.aisingapore.org",
    "https://ainowinstitute.org",
    "https://futureoflife.org",
    "https://www.unesco.org/en/artificial-intelligence",
    "https://www.hrw.org/topic/technology-and-rights",
    "https://www.eff.org/ai",
    "https://www.weforum.org/centre-for-the-fourth-industrial-revolution",
    "https://cset.georgetown.edu",
    "https://www.adalovelaceinstitute.org",
    "https://algorithmwatch.org",
    "https://x.com/elonmusk",
    "https://x.com/sama",
    "https://x.com/ylecun",
    "https://x.com/geoffreyhinton",
    "https://x.com/drfeifei",
    "https://x.com/tegmark",
    "https://x.com/AndrewYNg",
    "https://x.com/JeffDean",
    "https://x.com/GaryMarcus",
    "https://x.com/jeremyphoward",
    "https://x.com/lexfridman",
    "https://x.com/hardmaru",
    "https://x.com/goodfellow_ian",
    "https://x.com/timnitGebru",
    "https://x.com/ruchowdh",
    "https://x.com/karpathy",
    "https://x.com/demishassabis",
    "https://x.com/OpenAI",
    "https://x.com/GoogleAI",
    "https://x.com/MetaAI",
    "https://x.com/MSFTResearch",
    "https://x.com/NVIDIAAI",
    "https://x.com/huggingface",
    "https://x.com/StabilityAI",
    "https://x.com/DeepLearningAI",
    "https://www.reddit.com/r/MachineLearning",
    "https://www.reddit.com/r/artificial",
    "https://www.reddit.com/r/LanguageTechnology",
    "https://www.reddit.com/r/learnmachinelearning",
    "https://www.reddit.com/r/DeepLearning",
    "https://www.reddit.com/r/MLQuestions",
    "https://www.reddit.com/r/Computervision",
    "https://www.reddit.com/r/DataScience",
    "https://www.reddit.com/r/NeuralNetworks",
    "https://www.reddit.com/r/AIProgramming",
    "https://www.reddit.com/r/ChatGPT",
    "https://www.reddit.com/r/StableDiffusion",
    "https://www.reddit.com/r/AGI",
    "https://www.reddit.com/r/Robotics",
    "https://www.reddit.com/r/AIethics",
    "https://www.sequoiacap.com",
    "https://a16z.com",
    "https://www.khoslaventures.com",
    "https://www.baincapitalventures.com",
    "https://greylock.com/ai/",
    "https://www.nea.com/blog",
    "https://www.softbank.jp/en",
    "https://www.tigerglobal.com",
    "https://www.gv.com",
    "https://www.iqvia.com/solutions/research-and-development",
    "https://waymo.com/research",
    "https://www.qbitai.com",
    "https://www.jiqizhixin.com",
    "https://www.geekpark.net",
    "https://36kr.com",
    "https://www.import.io",
    "https://www.ai4good.org",
]


def is_valid_source(url):
    """
    Check if a URL is from a reliable domain by filtering out unreliable sources.
    Properly handles wildcard patterns like "*.breitbart.com"
    Args:
        url (str): The URL to validate

    Returns:
        bool: True if the source is valid (not in unreliable domain lists), False otherwise
    """
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc.lower()

    # Check if the URL is from an unreliable domain
    combined_set = GENERALLY_UNRELIABLE | DEPRECATED | BLACKLISTED

    for pattern in combined_set:
        pattern = pattern.lower()

        if pattern.startswith("*."):
            # Handle wildcard patterns like "*.breitbart.com"
            domain = pattern[2:]  # Remove the "*." prefix
            if netloc == domain or netloc.endswith("." + domain):
                return False
        else:
            # Handle exact patterns
            if pattern == netloc:
                return False

    return True


def filter_search_results(urls: List[str]) -> List[str]:
    """
    Filter a list of URLs, returning only valid sources.
    """
    return [url for url in urls if is_valid_source(url)]


def get_whitelisted_domains() -> List[str]:
    """
    Return the list of whitelisted domains for use with include_domains parameter.
    """
    return WHITELISTED_DOMAINS.copy()
