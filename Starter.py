import Log



def StartGui():






    if(PortOfSR830 is None):
        Log.LogMassage("Info","Startup","Try to Confic Port vor SR830", str(PortValueForSR830),"")
        ConficPorts(str(PortValueForSR830),BaudRateForSR830,TimeoutForSR830)
    
    
    if(PortOfSR830 is None):
        Log.LogMassage("Info","Startup","Try to Confic Port vor SR830", str(PortValueForSR830),"")
        ConficPorts(str(PortValueForSR830),BaudRateForSR830,TimeoutForSR830)
    


def ConficPorts(NameOfPort : str, BaudRate : int, Timeout : float):
    global SR830
    SR830 = serial.Serial(NameOfPort, BaudRate, timeout = Timeout)
    time.sleep (0.5)
    Log.LogMassage(NameOfPort,"Info","Test","OpenPort",str(BaudRate))