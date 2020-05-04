from discord.utils import find
from random import Random as RAND
from discord.ext import commands
import math


async def searchrole(roles:list,term:str):
    """Custom role search for discord.py"""
    role=find(lambda r: r.name.lower() == term.lower(), roles)
    if not role:
        role=find(lambda r: r.name.lower().startswith(term.lower()), roles)
    if not role:
        role=find(lambda r: term.lower() in r.name.lower(), roles)
    return role


def ordinal(n:int):
    """Turns an int into its ordinal (1 -> 1st)"""
    n="%d%s" % (n,"tsnrhtdd"[(math.floor(n/10)%10!=1)*(n%10<4)*n%10::4])  # noqa: E226,E228
    return n


class Config():
    @classmethod
    def statsserver(self):
        return int(702200971781996606)

    @classmethod
    def newguilds(self):
        return int(702201857606549646)

    @classmethod
    def errors(self):
        return int(702201821615358004)

    @classmethod
    def startup(self,name:str):
        if "beta" in name:
            return None
        else:
            return 702705386557276271

    @classmethod
    def DBLtoken(self):
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5MjczODkxNzIzNjk5ODE1NCIsImJvdCI6dHJ1ZSwiaWF0IjoxNTg3ODIzNjQ4fQ.qVqkmGa5inwLuosfNydxreptiF_UuIslfXTOxTkoFbI"

    @classmethod
    def avatar_ids(self):
        return [706686741423194123, 706686742505455686, 706686743340122173, 706686744317394996, 706686745550389359, 706686745789464648, 706686746594902057, 706686747551203348, 706686748276817930, 706686748973072405, 706686749836836955, 706686751179014174, 706686751879462972, 706686752366002239, 706686753335148575, 706686754224340992, 706686755209740308, 706686756069703710, 706686756770021386, 706686757495767052, 706686758493880410, 706686759500775514, 706686760238973079, 706686761107062914, 706686762218422292, 706686764302991422, 706686765192314980, 706686765854883890, 706686766593081381, 706686767486730341, 706686768333848625, 706686769050943550, 706686769734877204, 706686770359828510, 706686771106283540, 706686771773177966, 706686772154859531, 706686773094383726, 706686773819998218, 706686774491086928, 706686775195861123, 706686776013750363, 706686776714199160, 706686777397608469, 706686777922027531, 706686778907689041, 706686779608137799, 706686780228763738, 706686780925149195, 706686781692706856, 706686783106187274, 706686783349588050, 706686784372736081, 706686785081704611, 706686785811513404, 706686786495316039, 706686787170336778, 706686787992551438, 706686788869292538, 706686789200642130, 706686790962118656, 706686792274935878, 706686792782577686, 706686793478701107, 706686794443259954, 706686795202560040, 706686796330958949, 706686796767035435, 706686797899628634, 706686798394425395, 706686799786934272, 706686800546234458, 706686801074585642, 706686802135744596, 706686802735398924, 706686803524059238, 706686804346273903, 706686804971094027, 706686805562621984, 706686806464397333, 706686807471030343, 706686808263753738, 706686808771264533, 706686809685622795, 706686810452918312, 706686811157823580, 706686811992359003, 706686812994666587, 706686813665886269, 706686814341300265, 706686815502860359, 706686816321011752, 706686817059209226, 706686817805533254, 706686818275295305, 706686819202367537, 706686819835576340, 706686820565647491, 706686821689458758, 706686822582845440, 706686824164360273, 706686824692580353, 706686825988882523, 706686828014469200, 706686828677431399, 706686829348519947, 706686830422261810, 706686830703280179, 706686831852519554, 706686832318087219, 706686833660133416, 706686834373034034, 706686835505758229, 706686836705067018, 706686837208645797, 706686838269804554, 706686839339221082, 706686840161173564, 706686841042239559, 706686842065518622, 706686842979876945, 706686843822800903, 706686844389294193, 706686845752180767, 706686847106940969, 706686847874760774, 706686849896284160, 706686850579955762, 706686851284467744, 706686851829858377, 706686852870176798, 706686853604180048, 706686854258229268, 706686854656819331, 706686855864909854, 706686856875606047, 706686857517203489, 706686858112925697, 706686859367153684, 706686860008751105, 706686860583501915, 706686861367836765, 706686862248378401, 706686863058010192, 706686863846670346, 706686864911761469, 706686865721524264, 706686866518310952, 706686867252314113, 706686868019740712, 706686869596930078, 706686870557294622, 706686871488430160, 706686872109449227, 706686873007030312, 706686874063863898, 706686874969702470, 706686875905032202, 706686876756738129, 706686877297672243, 706686878304436315, 706686879164006501, 706686879931564075, 706686880888127598, 706686881487913021, 706686882335162378, 706686883102589018, 706686883693854781, 706686884939825162, 706686885614977064, 706686886499844136, 706686887011549284, 706686888223965244, 706686889113026670, 706686889821995069, 706686890614718584, 706686891067572295, 706686892195971073, 706686893114392656, 706686894066630677, 706686894825799782, 706686895815393310, 706686896507715605, 706686897346314261, 706686898453741651, 706686899120767050, 706686900043513857, 706686901259862076, 706686901905784892, 706686902677536841, 706686903499489300, 706686904178835516, 706686904514379836, 706686905714212864, 706686906439696384, 706686907182219324, 706686908092121178, 706686908981444708, 706686909572710482, 706686910676074547, 706686912399933470, 706686913138000033, 706686914085912576, 706686914501148673, 706686915511844894, 706686917437030431, 706686918259245146, 706686918703972453, 706686919937097759, 706686920612380773, 706686921497247745, 706686922453680201, 706686922931568713, 706686923984601168, 706686924546375772, 706686925834289152, 706686926651916338, 706686927507816568, 706686928312860692, 706686929214767145, 706686930435309600, 706686931601195138, 706686932394180698, 706686932968800257, 706686935355359232, 706686936219123732, 706686936672370809, 706686937427345459, 706686938685505576, 706686939247673385, 706686940371484783, 706686940862480437, 706686941755605004, 706686943160827925, 706686943886311524, 706686944872235029, 706686945790525684, 706686946574860338, 706686947334160394, 706686948260970576, 706686949393432597, 706686950144344084, 706686951016759396, 706686953323495434, 706686954678255676, 706686955760517221, 706686956595183726, 706686957484245042, 706686958377762906, 706686959225012325, 706686960869048450, 706686961804378112, 706686962567872581, 706686963453001778, 706686964765687818, 706686965600485376, 706686966829416529, 706686967823204353, 706686968683298847, 706686969685737502, 706686970688176208, 706686971501609040, 706686973519069235, 706686976182714419, 706686976937558096, 706686977503789078, 706686978497708062, 706686979349413919, 706686980561567764, 706686981777915944, 706686982780092498, 706686984025800745, 706686984986427423, 706686985447669852, 706686986437656689, 706686987620581446, 706686988602048534, 706686989616939151, 706686990384496741, 706686991370027088, 706686992427122728, 706686992901210173, 706686994042060891, 706686997330395196, 706686997875392564, 706686998731161631, 706686999779606558, 706687000526192650, 706687000937234503, 706687002132611143, 706687003055489125, 706687003638497291, 706687004590735410, 706687005404299344, 706687005974855691, 706687007073763359, 706687007581143158, 706687008470204547, 706687009397276763, 706687010202714160, 706687012266311690, 706687012912103477, 706687013977456660, 706687015047135313, 706687016099905617, 706687017051881472, 706687017970565230, 706687018704437298, 706687019476189208, 706687019853807687, 706687020633686027, 706687021535723602, 706687022655602708, 706687023716630538, 706687024463085669, 706687025838817341, 706687027046777176, 706687027806076968, 706687028347142216, 706687029563359344, 706687029940846684, 706687031178428426, 706687031933272064, 706687032814075945, 706687033308872807, 706687034311573605, 706687035330789407, 706687036475834368, 706687037209837578, 706687037864149064, 706687038937890856, 706687039596265473, 706687040837779516, 706687041806794772, 706687042330820719, 706687043576660018, 706687044075913218, 706687045199986800, 706687046105694328, 706687046940622858, 706687047812775996, 706687050039951370, 706687050446929981, 706687051403100201, 706687052846203003, 706687053655703572, 706687054330724433, 706687055182168086, 706687056432332870, 706687057170268240, 706687058919293059, 706687059708084294, 706687060509196389, 706687061704572949, 706687062937567402, 706687063508123689, 706687064548311170, 706687065366200370, 706687066146209822, 706687066989396019, 706687067882782800, 706687068931358780, 706687069937991811, 706687071246614558, 706687071972098079, 706687073029062696, 706687073670660158, 706687074656452618, 706687075470278737, 706687076183048294, 706687077231624202, 706687078326599690, 706687079156809819, 706687079966572584, 706687080998109255, 706687081581117534, 706687083003117618, 706687083766480906, 706687084647284776, 706687085465174056, 706687086220017755, 706687087101083738, 706687088052928513, 706687088711696485, 706687089940496554, 706687090917900368, 706687092415266827, 706687093107327007, 706687094264823919, 706687095124525076, 706687095976230922, 706687097045516308, 706687098077315103, 706687100887760896, 706687101990862889, 706687102959484968, 706687103752208404, 706687104838533181, 706687105387986985, 706687106696872007, 706687109788073995, 706687111041908847, 706687112170176562, 706687112954511430, 706687113785114674, 706687114749673542, 706687115764695070, 706687117215924245, 706687118113505321, 706687118789050448, 706687119552151562, 706687120684613662, 706687121636720650, 706687122278449184, 706687123524419654, 706687124509949953, 706687125399273512, 706687125940207637, 706687126967943298, 706687127827775518, 706687128545001533, 706687129761349834, 706687130356678720, 706687131535278120, 706687132365750272, 706687133397549177, 706687134467358730, 706687135511740528, 706687136635551754, 706687137390788671, 706687138204221453, 706687139244408894, 706687140137926747, 706687141198954588, 706687142293930025, 706687143212220416, 706687143703085179, 706687144776958023, 706687145703637062, 706687146563600435, 706687147448467516, 706687148207636520, 706687149038108752, 706687149919043614, 706687150778744888, 706687151777251379, 706687152758587422, 706687155572834375, 706687156197916824, 706687157426847824, 706687159486251139, 706687160711118898, 706687161663094864, 706687162673922058, 706687164511158313, 706687165618454578, 706687166729814046, 706687167484788780, 706687168613056542, 706687169019772960, 706687170118811728, 706687171054010468, 706687171826024510, 706687172987715664, 706687173805473832, 706687174711574648, 706687175420543038, 706687176271724574, 706687177668427816, 706687178733912115, 706687904403030046]


def prettydelta(seconds):
    seconds=int(seconds)
    days, seconds=divmod(seconds, 86400)
    hours, seconds=divmod(seconds, 3600)
    minutes, seconds=divmod(seconds, 60)
    if days > 0:
        return '%dd %dh%dm%ds' % (days, hours, minutes, seconds)
    elif hours > 0:
        return '%dh%dm%ds' % (hours, minutes, seconds)
    elif minutes > 0:
        return '%dm%ds' % (minutes, seconds)
    else:
        return '%ds' % (seconds,)


def prand(spice:float,uid:int,start:int,stop:int,inverse:bool=False):
    """Baised random"""
    if uid in [171197717559771136,692738917236998154]:
        if inverse:
            return start
        else:
            return stop
    else:
        b=uid * spice
        rng=RAND(x=(b))
        return rng.randint(start,stop)


# MUSIC ERRORS
class NoChannelProvided(commands.CommandError):
    """Error raised when no suitable voice channel was supplied."""
    pass


class IncorrectChannelError(commands.CommandError):
    """Error raised when commands are issued outside of the players session channel."""
    pass
