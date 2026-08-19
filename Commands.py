import serial
import time
import Log

def Setup ():
    Log = serial.Serial("COM4", 9600, timeout = 2.0)
    time.sleep (0.5)
                 
def getValue(Init,Command,i,j,k):


    match Command:
    # ==================================================================================    
    # Query the value of Aux Input i (1,2,3,4)
    # ==================================================================================
        case "OAUX1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX ? 1","SR830")
            Init.write(b"OAUX ? 1\r")
            ValueOAUX1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX1","SR830")
            return ValueOAUX1
        case "OAUX2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX ? 2","SR830")
            Init.write(b"OAUX ? 2\r")
            ValueOAUX2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX2","SR830")
            return ValueOAUX2
        case "OAUX3":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX ? 3","SR830")
            Init.write(b"OAUX ? 3\r")
            ValueOAUX3 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX3","SR830")
            return ValueOAUX3
        case "OAUX4":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX ? 4","SR830")
            Init.write(b"OAUX ? 4\r")
            ValueOAUX4 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()  
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX4","SR830")
            return ValueOAUX4 
    # ==================================================================================
    # Query the value of X (1), Y (2), R (3) or q (4). Returns ASCII floating point value
    # ==================================================================================                     
        case "OUTP1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OUTP? 1","SR830")
            Init.write(b"OUTP? 1\r")
            ValueOUTP1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()   
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOUTP1","SR830")
            return ValueOUTP1
        case "OUTP2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OUTP? 2","SR830")
            Init.write(b"OUTP? 2\r")
            ValueOUTP2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()                 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOUTP2","SR830")
            return ValueOUTP2
        case "OUTP3":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OUTP? 3","SR830")
            Init.write(b"OUTP? 3\r")
            ValueOUTP3 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()  
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOUTP3","SR830")
            return ValueOUTP3               
        case "OUTP4":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OUTP? 4","SR830")
            Init.write(b"OUTP? 4\r")
            ValueOUTP4 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOUTP4","SR830")
            return ValueOUTP4
    # ==================================================================================
    #  Query the value of Display i (1,2). Returns ASCII floating point value.
    # ==================================================================================                     
        case "OUTR1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OUTR? 1","SR830")
            Init.write(b"OUTR? 1\r")
            ValueOUTR1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()     
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOUTR1","SR830")
            return ValueOUTR1
        case "OUTR2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OUTR? 2","SR830")
            Init.write(b"OUTR? 2\r")
            ValueOUTR2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()                 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOUTR2","SR830")
            return ValueOUTR2
    # ==================================================================================
    #   Query the value of 2 thru 6 paramters at once.
    # ==================================================================================                     
        case "SNAP":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","SNAP?" + str(i) + "," + str(j),"SR830")
            Init.write(b"SNAP?" + str(i).encode() + b"," + str(j).encode() + b"\r")
            ValueSNAP = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueSNAP","SR830")
            return ValueSNAP    
    # ==================================================================================
    #   Query the value of Aux Input i (1,2,3,4). Returns ASCII floating point value
    # ==================================================================================                     
        case "OAUX1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX? 1","SR830")
            Init.write(b"OAUX? 1\r")
            ValueOAUX1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()    
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX1","SR830")
            return ValueOAUX1 
        case "OAUX2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX? 2","SR830")
            Init.write(b"OAUX? 2\r")
            ValueOAUX2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX2","SR830")
            return ValueOAUX2     
        case "OAUX3":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX? 3","SR830")
            Init.write(b"OAUX? 3\r")
            ValueOAUX3 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()      
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX3","SR830")
            return ValueOAUX3
        case "OAUX4":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX? 4","SR830")
            Init.write(b"OAUX? 4\r")
            ValueOAUX4 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX4","SR830")
            return ValueOAUX4                                                  
    # ==================================================================================
    #   Query the number of points stored in Display buffer.
    # ==================================================================================                     
        case "SPTS":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","SPTS?","SR830")
            Init.write(b"SPTS?\r")
            ValueSPTS = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()    
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueSPTS","SR830")
            return ValueSPTS
    # ==================================================================================
    #   Read k>=1 points starting at bin j>=0 from Display i (1,2) buffer in ASCII floating point
    # ==================================================================================                     
        case "TRCA1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","TRCA? 1," + str(j) + "," + str(k),"SR830")
            Init.write(b"TRCA? 1," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCA1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueTRCA1","SR830")
            return ValueTRCA1                       
        case "TRCA2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","TRCA? 2," + str(j) + "," + str(k),"SR830")
            Init.write(b"TRCA? 2," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCA2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueTRCA2","SR830")
            return ValueTRCA2        
    # ==================================================================================
    #    Read k>=1 points starting at bin j>=0 from Display i (1,2) buffer in IEEE binary floating point.
    # ==================================================================================                     
        case "TRCB1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","TRCB? 1," + str(j) + "," + str(k),"SR830")
            Init.write(b"TRCB? 1," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCB1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueTRCB1","SR830")
            return ValueTRCB1                      
        case "TRCB2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","TRCB? 2," + str(j) + "," + str(k),"SR830")
            Init.write(b"TRCB? 2," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCB2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueTRCB2","SR830")
            return ValueTRCB2
    # ==================================================================================
    #    Read k>=1 points starting at bin j>=0 from Display i (1,2) buffer in non-normalized binary floatingpoint.
    # ==================================================================================                     
        case "TRCL1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","TRCL? 1," + str(j) + "," + str(k),"SR830")
            Init.write(b"TRCL? 1," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCL1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()  
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueTRCL1","SR830")
            return ValueTRCL1                     
        case "TRCL2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","TRCL? 2," + str(j) + "," + str(k),"SR830")
            Init.write(b"TRCL? 2," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCL2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueTRCL2","SR830")
            return ValueTRCL2  
    # ==================================================================================
    #     Read the SR830 device identification string
    # ==================================================================================                     
        case "IDN?":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","IDN?","SR830")
            Init.write(b"IDN?\r")
            ValueIDN = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueIDN","SR830")
            return ValueIDN       
    # ==================================================================================
    #    Laser Actual Current   
    # ==================================================================================                     
        case "LCA":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LCA","OSTech")
            Init.write(b"LCA\r")
            ValueLCA = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLCA","OSTech")
            return ValueLCA   
    # ==================================================================================
    #    Laser Actual Voltage
    # ==================================================================================                     
        case "LVA":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LVA","OSTech")
            Init.write(b"LVA\r")
            ValueLVA = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLVA","OSTech")
            return ValueLVA   
    # ==================================================================================
    #   Laser photo Actual Current
    # ==================================================================================                     
        case "LPCA":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LPCA","OSTech")
            Init.write(b"LPCA\r")
            ValueLPCA = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLPCA","OSTech")
            return ValueLPCA   
    # ==================================================================================
    #    Laser photo Actual Power
    # ==================================================================================                     
        case "LPA":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LPA","OSTech")
            Init.write(b"LPA\r")
            ValueLPA = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLPA","OSTech")
            return ValueLPA   
    # ==================================================================================
    #    Laser fix procedure power
    # ==================================================================================                     
        case "LPF":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LPF","OSTech")
            Init.write(b"LPF\r")
            ValueLPF = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLPF","OSTech")
            return ValueLPF   
    # ==================================================================================
    #    Laser sequencer run
    # ==================================================================================                     
        case "LZR":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LZR","OSTech")
            Init.write(b"LZR\r")
            ValueLZR = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLZR","OSTech")
            return ValueLZR   
    # ==================================================================================
    #    Laser fix procedure power
    # ==================================================================================                     
        case "LPF":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LPF","OSTech")
            Init.write(b"LPF\r")
            ValueLPF = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLPF","OSTech")
            return ValueLPF   
    # ==================================================================================
    #    Laser actual temperature
    # ==================================================================================                     
        case "LPF":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LPF","OSTech")
            Init.write(b"LPF\r")
            ValueLPF = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLPF","OSTech")
            return ValueLPF   
    # ==================================================================================
    #    TEC actual current
    # ==================================================================================                     
        case "xTCA":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","xTCA","OSTech")
            Init.write(b"xTCA\r")
            ValuexTCA = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValuexTCA","OSTech")
            return ValuexTCA           
    # ==================================================================================
    #    TEC actual Value
    # ==================================================================================                     
        case "xTVA":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","xTVA","OSTech")
            Init.write(b"xTVA\r")
            ValuexTVA = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValuexTVA","OSTech")
            return ValuexTVA   
    # ==================================================================================
    #    Set Defaults
    # ==================================================================================                     
        case "GD":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","GD","OSTech")
            Init.write(b"GD\r")
            ValueGD = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueGD","OSTech")
            return ValueGD   
    # ==================================================================================
    #    Device Temperature
    # ==================================================================================                     
        case "GT":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","GT","OSTech")
            Init.write(b"GT\r")
            ValueGT = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueGT","OSTech")
            return ValueGT  
    # ==================================================================================
    #    Software Version
    # ==================================================================================                     
        case "GVS":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","GVS","OSTech")
            Init.write(b"GVS\r")
            ValueGVS = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueGVS","OSTech")
            return ValueGVS      
    # ==================================================================================
    #    Serial Number
    # ==================================================================================                     
        case "GVN":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","GVN","OSTech")
            Init.write(b"GVN\r")
            ValueGVN = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueGVN","OSTech")
            return ValueGVN  
    # ==================================================================================
    #    Get Status
    # ==================================================================================                     
        case "GS":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","GS","OSTech")
            Init.write(b"GS\r")
            ValueGS = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueGS","OSTech")
            return ValueGS 
    # ==================================================================================
    #    Get Mode
    # ==================================================================================                     
        case "GM":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","GM","OSTech")
            Init.write(b"GM\r")
            ValueGM = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueGM","OSTech")
            return ValueGM  

                 

def setValue(Init,Command,i,j,k,l,m,f,x,y,z,s):

    match Command:

        case "PHAS":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","PHAS " + str(x),"SR830")
            Init.write(b"PHAS " + str(x).encode() + b"\r")
            ValuePHAS = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","ValuePHAS","SR830")
            return ValuePHAS
        case "FMOD":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","FMOD " + str(i),"SR830")
            Init.write(b"FMOD " + str(i).encode() + b"\r")
            ValueFMOD = Init.readuntil(b"\r").decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","ValueFMOD","SR830")
            return ValueFMOD