import  time
def LogMassage(TAG:str,Category:str,Massage:str,INFO:str,AdditionalInfo:str):
        print(time.strftime("%Y-%m-%d %H:%M:%S")+ "  |  " + TAG + "  |  " + Category + "  |  " + Massage + "  |  " + AdditionalInfo)