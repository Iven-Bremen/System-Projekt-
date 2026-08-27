import serial
import time
import Log
import GUI
from typing import Optional


def getValue(Init, Command: str, i: Optional[int] = 0, j: Optional[int] = 0, k: Optional[int] = 0)-> str:
    """
    Liest Werte von verbundenen Hardware-Geräten (SR830 / OSTech) aus.

    ---
    ### Verfügbare Commands (Verwendungsübersicht):

    **SR830 Lock-In-Verstärker:**
    * `OAUX1` - `OAUX4`: Query Aux Input i (1-4)
    * `OUTP1` - `OUTP4`: Query X (1), Y (2), R (3) or theta (4)
    * `OUTR1`, `OUTR2`: Query Display i (1,2)
    * `SNAP`: Query 2-6 parameters at once (uses i, j)
    * `SPTS`: Query number of points in Display buffer
    * `TRCA1`, `TRCA2`: Read points (ASCII) from buffer (uses j=start, k=count)
    * `TRCB1`, `TRCB2`: Read points (IEEE binary float) from buffer (uses j, k)
    * `TRCL1`, `TRCL2`: Read points (non-norm binary float) from buffer (uses j, k)
    * `IDN`: Read device identification string

    **OSTech Laser / TEC Controller:**
    * `LCA`: Laser Actual Current
    * `LVA`: Laser Actual Voltage
    * `LPCA`: Laser photo Actual Current
    * `LPA`: Laser photo Actual Power
    * `LPF`: Laser fix procedure power
    * `LZR`: Laser sequencer run
    * `xTCA`: TEC actual current
    * `xTVA`: TEC actual Value
    * `GD`: Set Defaults / Get Defaults
    * `GT`: Device Temperature
    * `GVS`: Software Version
    * `GVN`: Serial Number
    * `GS`: Get Status
    * `GM`: Get Mode
    """
    from Starter import SR830, OSTech    
    # Abfangen, falls keine Hardware verbunden ist
    if Init is None:
        Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"), "Communication", "GetValue", f"Keine Hardware für {Command} verbunden!", str(Init))
        return "N/A"  # Dummy-Wert für die GUI

    match Command:
    # ==================================================================================    
    # Query the value of Aux Input i (1,2,3,4)
    # ==================================================================================
        case "OAUX1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX ? 1","SR830")
            SR830.write(b"OAUX? 1\r")
            ValueOAUX1 = SR830.read_until(b"\r")
            ValueOAUX1 = ValueOAUX1.decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX1","SR830")
            return ValueOAUX1
        case "OAUX2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX ? 2","SR830")
            SR830.write(b"OAUX? 2\r")
            ValueOAUX2 = SR830.read_until(b"\r")
            ValueOAUX2 = ValueOAUX2.decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX2","SR830")
            return ValueOAUX2
        case "OAUX3":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX ? 3","SR830")
            SR830.write(b"OAUX? 3\r")
            ValueOAUX3 = SR830.read_until(b"\r")
            ValueOAUX3 = ValueOAUX3.decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX3","SR830")
            return ValueOAUX3
        case "OAUX4":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX ? 4","SR830")
            SR830.write(b"OAUX? 4\r")
            ValueOAUX4 = SR830.read_until(b"\r")
            ValueOAUX4 = ValueOAUX4.decode("ascii", errors="replace").strip()  
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX4","SR830")
            return ValueOAUX4 
    # ==================================================================================
    # Query the value of X (1), Y (2), R (3) or q (4). Returns ASCII floating point value
    # ==================================================================================                     
        case "OUTP1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OUTP? 1","SR830")
            SR830.write(b"OUTP? 1\r")
            ValueOUTP1 = SR830.read_until(b"\r")
            ValueOUTP1 = ValueOUTP1.decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue",str(ValueOUTP1),"SR830")
            return ValueOUTP1
        case "OUTP2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OUTP? 2","SR830")
            SR830.write(b"OUTP? 2\r")
            ValueOUTP2 = SR830.read_until(b"\r")
            ValueOUTP2 = ValueOUTP2.decode("ascii", errors="replace").strip()                 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOUTP2","SR830")
            return ValueOUTP2
        case "OUTP3":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OUTP? 3","SR830")
            SR830.write(b"OUTP? 3\r")
            ValueOUTP3 = SR830.read_until(b"\r")
            ValueOUTP3 = ValueOUTP3.decode("ascii", errors="replace").strip()  
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOUTP3","SR830")
            return ValueOUTP3               
        case "OUTP4":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OUTP? 4","SR830")
            SR830.write(b"OUTP? 4\r")
            ValueOUTP4 = SR830.readuntil(b"\r")
            ValueOUTP4 = ValueOUTP4.decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOUTP4","SR830")
            return ValueOUTP4
    # ==================================================================================
    #  Query the value of Display i (1,2). Returns ASCII floating point value.
    # ==================================================================================                     
        case "OUTR1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OUTR? 1","SR830")
            SR830.write(b"OUTR? 1\r")
            ValueOUTR1 = SR830.read_until(b"\r")
            ValueOUTR1 = ValueOUTR1.decode("ascii", errors="replace").strip()     
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOUTR1","SR830")
            return ValueOUTR1
        case "OUTR2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OUTR? 2","SR830")
            SR830.write(b"OUTR? 2\r")
            ValueOUTR2 = SR830.read_until(b"\r")
            ValueOUTR2 = ValueOUTR2.decode("ascii", errors="replace").strip()                 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOUTR2","SR830")
            return ValueOUTR2
    # ==================================================================================
    #   Query the value of 2 thru 6 paramters at once.
    # ==================================================================================                     
        case "SNAP":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","SNAP?" + str(i) + "," + str(j),"SR830")
            SR830.write(b"SNAP?" + str(i).encode() + b"," + str(j).encode() + b"\r")
            ValueSNAP = SR830.read_until(b"\r")
            ValueSNAP = ValueSNAP.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueSNAP","SR830")
            return ValueSNAP    
    # ==================================================================================
    #   Query the value of Aux Input i (1,2,3,4). Returns ASCII floating point value
    # ==================================================================================                     
        case "OAUX1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX? 1","SR830")
            SR830.write(b"OAUX? 1\r")
            ValueOAUX1 = SR830.read_until(b"\r")
            ValueOAUX1 = ValueOAUX1.decode("ascii", errors="replace").strip()    
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX1","SR830")
            return ValueOAUX1 
        case "OAUX2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX? 2","SR830")
            SR830.write(b"OAUX? 2\r")
            ValueOAUX2 = SR830.read_until(b"\r")
            ValueOAUX2 = ValueOAUX2.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX2","SR830")
            return ValueOAUX2     
        case "OAUX3":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX? 3","SR830")
            SR830.write(b"OAUX? 3\r")
            ValueOAUX3 = SR830.read_until(b"\r")
            ValueOAUX3 = ValueOAUX3.decode("ascii", errors="replace").strip()      
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX3","SR830")
            return ValueOAUX3
        case "OAUX4":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","OAUX? 4","SR830")
            SR830.write(b"OAUX? 4\r")
            ValueOAUX4 = SR830.read_until(b"\r")
            ValueOAUX4 = ValueOAUX4.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueOAUX4","SR830")
            return ValueOAUX4                                                  
    # ==================================================================================
    #   Query the number of points stored in Display buffer.
    # ==================================================================================                     
        case "SPTS":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","SPTS?","SR830")
            SR830.write(b"SPTS?\r")
            ValueSPTS = SR830.read_until(b"\r")
            ValueSPTS = ValueSPTS.decode("ascii", errors="replace").strip()    
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueSPTS","SR830")
            return ValueSPTS
    # ==================================================================================
    #   Read k>=1 points starting at bin j>=0 from Display i (1,2) buffer in ASCII floating point
    # ==================================================================================                     
        case "TRCA1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","TRCA? 1," + str(j) + "," + str(k),"SR830")
            SR830.write(b"TRCA? 1," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCA1 = SR830.read_until(b"\r")
            ValueTRCA1 = ValueTRCA1.decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueTRCA1","SR830")
            return ValueTRCA1                       
        case "TRCA2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","TRCA? 2," + str(j) + "," + str(k),"SR830")
            SR830.write(b"TRCA? 2," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCA2 = SR830.read_until(b"\r")
            ValueTRCA2 = ValueTRCA2.decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueTRCA2","SR830")
            return ValueTRCA2        
    # ==================================================================================
    #    Read k>=1 points starting at bin j>=0 from Display i (1,2) buffer in IEEE binary floating point.
    # ==================================================================================                     
        case "TRCB1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","TRCB? 1," + str(j) + "," + str(k),"SR830")
            SR830.write(b"TRCB? 1," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCB1 = SR830.read_until(b"\r")
            ValueTRCB1 = ValueTRCB1.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueTRCB1","SR830")
            return ValueTRCB1                      
        case "TRCB2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","TRCB? 2," + str(j) + "," + str(k),"SR830")
            SR830.write(b"TRCB? 2," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCB2 = SR830.read_until(b"\r")
            ValueTRCB2 = ValueTRCB2.decode("ascii", errors="replace").strip()
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueTRCB2","SR830")
            return ValueTRCB2
    # ==================================================================================
    #    Read k>=1 points starting at bin j>=0 from Display i (1,2) buffer in non-normalized binary floatingpoint.
    # ==================================================================================                     
        case "TRCL1":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","TRCL? 1," + str(j) + "," + str(k),"SR830")
            SR830.write(b"TRCL? 1," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCL1 = SR830.read_until(b"\r")
            ValueTRCL1 = ValueTRCL1.decode("ascii", errors="replace").strip()  
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueTRCL1","SR830")
            return ValueTRCL1                     
        case "TRCL2":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","TRCL? 2," + str(j) + "," + str(k),"SR830")
            SR830.write(b"TRCL? 2," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCL2 = SR830.read_until(b"\r")
            ValueTRCL2 = ValueTRCL2.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueTRCL2","SR830")
            return ValueTRCL2  
    # ==================================================================================
    #     Read the SR830 device identification string
    # ==================================================================================                     
        case "IDN":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","IDN?","SR830")
            SR830.write(b"*IDN?\r")
            ValueIDN = SR830.read_until(b"\r")
            ValueIDN = ValueIDN.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"), "Communication", "GetValue", str(ValueIDN), "SR830")
            return ValueIDN       
    # ==================================================================================
    #    Laser Actual Current   
    # ==================================================================================                     
        case "LCA":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LCA","OSTech")
            OSTech.write(b"LCA\r")
            ValueLCA = OSTech.read_until(b"\r")
            ValueLCA = ValueLCA.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLCA","OSTech")
            return ValueLCA   
    # ==================================================================================
    #    Laser Actual Voltage
    # ==================================================================================                     
        case "LVA":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LVA","OSTech")
            OSTech.write(b"LVA\r")
            ValueLVA = OSTech.read_until(b"\r")
            ValueLVA = ValueLVA.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLVA","OSTech")
            return ValueLVA   
    # ==================================================================================
    #   Laser photo Actual Current
    # ==================================================================================                     
        case "LPCA":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LPCA","OSTech")
            OSTech.write(b"LPCA\r")
            ValueLPCA = OSTech.read_until(b"\r")
            ValueLPCA = ValueLPCA.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLPCA","OSTech")
            return ValueLPCA   
    # ==================================================================================
    #    Laser photo Actual Power
    # ==================================================================================                     
        case "LPA":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LPA","OSTech")
            OSTech.write(b"LPA\r")
            ValueLPA = OSTech.read_until(b"\r")
            ValueLPA = ValueLPA.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLPA","OSTech")
            return ValueLPA   
    # ==================================================================================
    #    Laser fix procedure power
    # ==================================================================================                     
        case "LPF":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LPF","OSTech")
            OSTech.write(b"LPF\r")
            ValueLPF = OSTech.read_until(b"\r")
            ValueLPF = ValueLPF.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLPF","OSTech")
            return ValueLPF   
    # ==================================================================================
    #    Laser sequencer run
    # ==================================================================================                     
        case "LZR":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LZR","OSTech")
            OSTech.write(b"LZR\r")
            ValueLZR = OSTech.read_until(b"\r")
            ValueLZR = ValueLZR.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLZR","OSTech")
            return ValueLZR   
    # ==================================================================================
    #    Laser fix procedure power
    # ==================================================================================                     
        case "LPF":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LPF","OSTech")
            OSTech.write(b"LPF\r")
            ValueLPF = OSTech.read_until(b"\r")
            ValueLPF = ValueLPF.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLPF","OSTech")
            return ValueLPF   
    # ==================================================================================
    #    Laser actual temperature
    # ==================================================================================                     
        case "LPF":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","LPF","OSTech")
            OSTech.write(b"LPF\r")
            ValueLPF = OSTech.read_until(b"\r")
            ValueLPF = ValueLPF.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueLPF","OSTech")
            return ValueLPF   
    # ==================================================================================
    #    TEC actual current
    # ==================================================================================                     
        case "xTCA":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","xTCA","OSTech")
            OSTech.write(b"xTCA\r")
            ValuexTCA = OSTech.read_until(b"\r")
            ValuexTCA = ValuexTCA.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValuexTCA","OSTech")
            return ValuexTCA           
    # ==================================================================================
    #    TEC actual Value
    # ==================================================================================                     
        case "xTVA":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","xTVA","OSTech")
            OSTech.write(b"xTVA\r")
            ValuexTVA = OSTech.read_until(b"\r")
            ValuexTVA = ValuexTVA.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValuexTVA","OSTech")
            return ValuexTVA   
    # ==================================================================================
    #    Set Defaults
    # ==================================================================================                     
        case "GD":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","GD","OSTech")
            OSTech.write(b"GD\r")
            ValueGD = OSTech.read_until(b"\r")
            ValueGD = ValueGD.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueGD","OSTech")
            return ValueGD   
    # ==================================================================================
    #    Device Temperature
    # ==================================================================================                     
        case "GT":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","GT","OSTech")
            OSTech.write(b"GT\r")
            ValueGT = OSTech.read_until(b"\r")
            ValueGT = ValueGT.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueGT","OSTech")
            return ValueGT  
    # ==================================================================================
    #    Software Version
    # ==================================================================================                     
        case "GVS":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","GVS","OSTech")
            OSTech.write(b"GVS\r")
            ValueGVS = OSTech.read_until(b"\r")
            ValueGVS = ValueGVS.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueGVS","OSTech")
            return ValueGVS      
    # ==================================================================================
    #    Serial Number
    # ==================================================================================                     
        case "GVN":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","GVN","OSTech")
            OSTech.write(b"GVN\r")
            ValueGVN = OSTech.read_until(b"\r")
            ValueGVN = ValueGVN.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueGVN","OSTech")
            return ValueGVN  
    # ==================================================================================
    #    Get Status
    # ==================================================================================                     
        case "GS":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","GS","OSTech")
            OSTech.write(b"GS\r")
            ValueGS = OSTech.read_until(b"\r")
            ValueGS = ValueGS.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueGS","OSTech")
            return ValueGS 
    # ==================================================================================
    #    Get Mode
    # ==================================================================================                     
        case "GM":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","GM","OSTech")
            OSTech.write(b"GM\r")
            ValueGM = OSTech.read_until(b"\r")
            ValueGM = ValueGM.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","GetValue","ValueGM","OSTech")
            return ValueGM  

                 

def setValue(Init,Command:str,i: Optional[int] = 0,j: Optional[int] = 0,k: Optional[int] = 0,l: Optional[int] = 0,m: Optional[int] = 0,f: Optional[int] = 0,x: Optional[int] = 0,y: Optional[int] = 0,z: Optional[int] = 0,s: Optional[int] = 0)-> str:
    """
    Setzt Werte auf verbundenen Hardware-Geräten (SR830 / OSTech).

    ---
    ### Verfügbare Commands (Verwendungsübersicht):

    **SR830 Lock-In-Verstärker:**
    * `PHAS` - `PHAS`: 
    * `FMOD` - `FMOD`: 
    """
    from Starter import SR830, OSTech

        # Abfangen, falls keine Hardware verbunden ist
    if Init is None:
        Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"), "Communication", "GetValue", f"Keine Hardware für {Command} verbunden!", str(Init))
        return "N/A"  # Dummy-Wert für die GUI


    match Command:
        # ==================================================================================
        #   Set (Query) the Phase Shift to x degrees
        # ==================================================================================                    
        case "PHAS":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","PHAS " + str(x),"SR830")
            SR830.write(b"PHAS " + str(x).encode() + b"\r")
            ValuePHAS = SR830.read_until(b"\r")
            ValuePHAS = ValuePHAS.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValuePHAS),"SR830")
            return ValuePHAS
        # ==================================================================================
        #    Set (Query) the Reference Source to External (0) or Internal (1).
        # ==================================================================================            
        case "FMOD":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","FMOD " + str(i),"SR830")
            SR830.write(b"FMOD " + str(i).encode() + b"\r")
            ValueFMOD = SR830.read_until(b"\r")
            ValueFMOD = ValueFMOD.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueFMOD),"SR830")
            return ValueFMOD
        # ==================================================================================
        #    Set (Query) the Reference Frequency to f Hz.Set only in Internal reference mode
        # ==================================================================================    
        case "FREQ":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","FREQ " + str(i),"SR830")
            SR830.write(b"FREQ " + str(i).encode() + b"\r")
            ValueFREQ = SR830.read_until(b"\r")
            ValueFREQ = ValueFREQ.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueFREQ),"SR830")
            return ValueFREQ
        # ==================================================================================
        #   Set (Query) the External Reference Slope to Sine(0), TTL Rising (1), or TTL Falling (2).
        # ==================================================================================                
        case "RSLP":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","RSLP " + str(i),"SR830")
            SR830.write(b"RSLP " + str(i).encode() + b"\r")
            ValueRSLP = SR830.read_until(b"\r")
            ValueRSLP = ValueRSLP.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueRSLP),"SR830")
            return ValueRSLP     
        # ==================================================================================
        #    Set (Query) the Detection Harmonic to 1 ≤ i ≤ 19999 and i•f ≤ 102 kHz.
        # ==================================================================================                
        case "HARM":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","HARM " + str(i),"SR830")
            SR830.write(b"HARM " + str(i).encode() + b"\r")
            ValueHARM = SR830.read_until(b"\r")
            ValueHARM = ValueHARM.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueHARM),"SR830")
            return ValueHARM
        # ==================================================================================
        #     Set (Query) the Sine Output Amplitude to x Vrms. 0.004 ≤ x ≤5.000.
        # ==================================================================================                
        case "SLVL":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","SLVL " + str(x),"SR830")
            SR830.write(b"SLVL " + str(x).encode() + b"\r")
            ValueSLVL = SR830.read_until(b"\r")
            ValueSLVL = ValueSLVL.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueSLVL),"SR830")
            return ValueSLVL                               
        # ==================================================================================
        #    Set (Query) the Input Configuration to A (0), A-B (1) , I (1 MΩ) (2) or I (100 MΩ) (3).
        # ==================================================================================                
        case "ISRC":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","ISRC " + str(i),"SR830")
            SR830.write(b"ISRC " + str(i).encode() + b"\r")
            ValueISRC = SR830.read_until(b"\r")
            ValueISRC = ValueISRC.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueISRC),"SR830")
            return ValueISRC            
        # ==================================================================================
        #     Set (Query) the Input Shield Grounding to Float (0) or Ground (1).
        # ==================================================================================                
        case "IGND":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","IGND " + str(i),"SR830")
            SR830.write(b"IGND " + str(i).encode() + b"\r")
            ValueIGND = SR830.read_until(b"\r")
            ValueIGND = ValueIGND.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueIGND),"SR830")
            return ValueIGND       
        # ==================================================================================
        #    Set (Query) the Input Coupling to AC (0) or DC (1).
        # ==================================================================================                
        case "LCPL":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","LCPL " + str(i),"SR830")
            SR830.write(b"LCPL " + str(i).encode() + b"\r")
            ValueLCPL = SR830.read_until(b"\r")
            ValueLCPL = ValueLCPL.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueLCPL),"SR830")
            return ValueLCPL
        # ==================================================================================
        #     Set (Query) the Line Notch Filters to Out (0), Line In (1) , 2xLine In (2), or Both In (3)
        # ==================================================================================                
        case "ILN":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","ILN " + str(i),"SR830")
            SR830.write(b"ILN " + str(i).encode() + b"\r")
            ValueILN = SR830.read_until(b"\r")
            ValueILN= ValueILN.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueILN),"SR830")
            return ValueILN
        # ==================================================================================
        #     Set (Query) the Sensitivity to 2 nV (0) through 1 V (26) rms full scale.
        # ==================================================================================                
        case "SENS":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","SENS " + str(i),"SR830")
            SR830.write(b"SENS " + str(i).encode() + b"\r")
            ValueSENS = SR830.read_until(b"\r")
            ValueSENS = ValueSENS.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueSENS),"SR830")
            return ValueSENS
        # ==================================================================================
        #    Set (Query) the Dynamic Reserve Mode to HighReserve (0), Normal (1), or Low Noise (2)
        # ==================================================================================                
        case "RMOD":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","RMOD " + str(i),"SR830")
            SR830.write(b"RMOD " + str(i).encode() + b"\r")
            ValueRMOD = SR830.read_until(b"\r")
            ValueRMOD = ValueRMOD.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueRMOD),"SR830")
            return ValueRMOD
        # ==================================================================================
        #    Set (Query) the Time Constant to 10 µs (0) through 30 ks (19)
        # ==================================================================================                
        case "OFLT":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","OFLT " + str(i),"SR830")
            SR830.write(b"OFLT " + str(i).encode() + b"\r")
            ValueOFLT = SR830.read_until(b"\r")
            ValueOFLT = ValueOFLT.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueOFLT),"SR830")
            return ValueOFLT
        # ==================================================================================
        #    Set (Query) the Low Pass Filter Slope to 6 (0), 12 (1), 18 (2) or 24 (3) dB/oct.
        # ==================================================================================                
        case "OFSL":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","OFSL " + str(i),"SR830")
            SR830.write(b"OFSL " + str(i).encode() + b"\r")
            ValueOFSL = SR830.read_until(b"\r")
            ValueOFSL = ValueOFSL.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueOFSL),"SR830")
            return ValueOFSL
        # ==================================================================================
        #    Set (Query) the Synchronous Filter to Off (0) or On below 200 Hz (1).
        # ==================================================================================                
        case "SYNC":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","SYNC " + str(i),"SR830")
            SR830.write(b"SYNC " + str(i).encode() + b"\r")
            ValueSYNC = SR830.read_until(b"\r")
            ValueSYNC = ValueSYNC.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueSYNC),"SR830")
            return ValueSYNC
        # ==================================================================================
        #     Set (Query) the CH1 or CH2 (i=1,2) display to XY, Rθ, XnYn, Aux 1,3 or Aux 2,4 (j=0..4) and ratio the display to None, Aux1,3 or Aux 2,4 (k=0,1,2).
        # ==================================================================================                
        case "DDEF":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","DDEF " + str(i) + str(j) + str(k),"SR830")
            SR830.write(b"DDEF " + str(i).encode() + str(j).encode() + str(k).encode() + b"\r")
            ValueDDEF = SR830.read_until(b"\r")
            ValueDDEF = ValueDDEF.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueDDEF),"SR830")
            return ValueDDEF
        # ==================================================================================
        #    Set (Query) the CH1 (i=1) or CH2 (i=2) Output Source to X or Y (j=1) or Display (j=0)
        # ==================================================================================                
        case "FPOP":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","FPOP " + str(i) + str(j),"SR830")
            SR830.write(b"FPOP " + str(i).encode() + str(j).encode() + b"\r")
            ValueFPOP = SR830.read_until(b"\r")
            ValueFPOP = ValueFPOP.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueFPOP),"SR830")
            return ValueFPOP
        # ==================================================================================
        #    Set (Query) the X, Y, R (i=1,2,3) Offset to x percent ( -105.00 ≤ x ≤ 105.00) and Expand to 1, 10 or 100 (j=0,1,2).
        # ==================================================================================                
        case "OEXP":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","OEXP " + str(i) + str(x)+ str(j),"SR830")
            SR830.write(b"OEXP " + str(i).encode() + str(x).encode() + str(j).encode() + b"\r")
            ValueOEXP = SR830.read_until(b"\r")
            ValueOEXP = ValueOEXP.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueOEXP),"SR830")
            return ValueOEXP
        # ==================================================================================
        #    Auto Offset X, Y, R (i=1,2,3).
        # ==================================================================================                
        case "AOFF":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","AOFF " + str(i),"SR830")
            SR830.write(b"AOFF " + str(i).encode() + b"\r")
            ValueAOFF = SR830.read_until(b"\r")
            ValueAOFF = ValueAOFF.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueAOFF),"SR830")
            return ValueAOFF
        # ==================================================================================
        #    Set (Query) voltage of Aux Output i (1,2,3,4) to x Volts. -10.500 ≤ x ≤ 10.500. 
        # ==================================================================================                
        case "AUXV":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","AUXV " + str(i) + " " + str(x),"SR830")
            SR830.write(b"AUXV " + str(i).encode() +  str(x).encode() + b"\r")
            ValueAUXV = SR830.read_until(b"\r")
            ValueAUXV = ValueAUXV.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueAUXV),"SR830")
            return ValueAUXV
        # ==================================================================================
        #     Set (Query) the Output Interface to RS232 (0) or GPIB (1)
        # ==================================================================================                
        case "OUTX":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","OUTX " + str(i),"SR830")
            SR830.write(b"OUTX " + str(i).encode() + b"\r")
            ValueOUTX = SR830.read_until(b"\r")
            ValueOUTX = ValueOUTX.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueOUTX),"SR830")
            return ValueOUTX
        # ==================================================================================
        #     Set (Query) the GPIB Overide Remote state to Off (0) or On (1)
        # ==================================================================================                
        case "OVRM":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","OVRM " + str(i),"SR830")
            SR830.write(b"OVRM " + str(i).encode() + b"\r")
            ValueOVRM = SR830.read_until(b"\r")
            ValueOVRM = ValueOVRM.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueOVRM),"SR830")
            return ValueOVRM
        # ==================================================================================
        #     Set (Query) the Key Click to Off (0) or On (1).
        # ==================================================================================                
        case "AOFF":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","AOFF " + str(i),"SR830")
            SR830.write(b"AOFF " + str(i).encode() + b"\r")
            ValueAOFF = SR830.read_until(b"\r")
            ValueAOFF = ValueAOFF.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueAOFF),"SR830")
            return ValueAOFF
        # ==================================================================================
        #     Set (Query) voltage of Aux Output i (1,2,3,4) to x Volts. -10.500 ≤ x ≤ 10.500. 
        # ==================================================================================                
        case "AOXV":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","AOXV " + str(i) + " " + str(x),"SR830")
            SR830.write(b"AOXV " + str(i).encode() + str(x).encode() + b"\r")
            ValueAOXV = SR830.read_until(b"\r")
            ValueAOXV = ValueAOXV.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueAOXV),"SR830")
            return ValueAOXV
        # ==================================================================================
        #    Set (Query) the Output Interface to RS232 (0) or GPIB (1)
        # ==================================================================================                
        case "OUTX":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","OUTX " + str(i),"SR830")
            SR830.write(b"OUTX " + str(i).encode() + b"\r")
            ValueOUTX = SR830.read_until(b"\r")
            ValueOUTX = ValueOUTX.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueOUTX),"SR830")
            return ValueOUTX
        # ==================================================================================
        #    Set (Query) the GPIB Overide Remote state to Off (0) or On (1)
        # ==================================================================================                
        case "OVRM":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","OVRM " + str(i),"SR830")
            SR830.write(b"OVRM " + str(i).encode() + b"\r")
            ValueOVRM = SR830.read_until(b"\r")
            ValueOVRM = ValueOVRM.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueOVRM),"SR830")
            return ValueOVRM
        # ==================================================================================
        #    Set (Query) the Key Click to Off (0) or On (1)
        # ==================================================================================                
        case "KCLK":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","KCLK " + str(i),"SR830")
            SR830.write(b"KCLK " + str(i).encode() + b"\r")
            ValueKCLK = SR830.read_until(b"\r")
            ValueKCLK = ValueKCLK.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueKCLK),"SR830")
            return ValueKCLK
        # ==================================================================================
        #    Set (Query) the Alarms to Off (0) or On (1).
        # ==================================================================================                
        case "ALRM":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","ALRM " + str(i),"SR830")
            SR830.write(b"ALRM " + str(i).encode() + b"\r")
            ValueALRM = SR830.read_until(b"\r")
            ValueALRM = ValueALRM.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueALRM),"SR830")
            return ValueALRM
        # ==================================================================================
        #    Save current setup to setting buffer i (1≤i≤9).
        # ==================================================================================                
        case "SSET":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","SSET " + str(i),"SR830")
            SR830.write(b"SSET " + str(i).encode() + b"\r")
            ValueSSET = SR830.read_until(b"\r")
            ValueSSET = ValueSSET.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueSSET),"SR830")
            return ValueSSET
        # ==================================================================================
        #    Recall current setup from setting buffer i (1≤i≤9).
        # ==================================================================================                
        case "RSET":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","RSET " + str(i),"SR830")
            SR830.write(b"RSET " + str(i).encode() + b"\r")
            ValueRSET = SR830.read_until(b"\r")
            ValueRSET = ValueRSET.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueRSET),"SR830")
            return ValueRSET
        # ==================================================================================
        #    Auto Gain function. Same as pressing the [AUTO GAIN] key
        # ==================================================================================                
        case "AGAN":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","AGAN ","SR830")
            SR830.write(b"AGAN " + b"\r")
            ValueAGAN = SR830.read_until(b"\r")
            ValueAGAN = ValueAGAN.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueAGAN),"SR830")
            return ValueAGAN
        # ==================================================================================
        #    Auto Reserve function. Same as pressing the [AUTO RESERVE] key
        # ==================================================================================                
        case "ARSV":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","ARSV ","SR830")
            SR830.write(b"ARSV " + b"\r")
            ValueARSV = SR830.read_until(b"\r")
            ValueARSV = ValueARSV.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueARSV),"SR830")
            return ValueARSV
        # ==================================================================================
        #    
        # ==================================================================================                
        case "AOFF":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","AOFF " + str(i),"SR830")
            SR830.write(b"AOFF " + str(i).encode() + b"\r")
            ValueAOFF = SR830.read_until(b"\r")
            ValueAOFF = ValueAOFF.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","ValueAOFF","SR830")
            return ValueAOFF
        # ==================================================================================
        #     Auto Phase function. Same as pressing the [AUTO PHASE] key.
        # ==================================================================================                
        case "APHS":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","APHS ","SR830")
            SR830.write(b"APHS " + b"\r")
            ValueAPHS = SR830.read_until(b"\r")
            ValueAPHS = ValueAPHS.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue",str(ValueAPHS),"SR830")
            return ValueAPHS
        # ==================================================================================
        #     Auto Offset X,Y or R (i=1,2,3)
        # ==================================================================================                
        case "AOFF":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","AOFF " + str(i),"SR830")
            SR830.write(b"AOFF " + str(i).encode() + b"\r")
            ValueAOFF = SR830.read_until(b"\r")
            ValueAOFF = ValueAOFF.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","ValueAOFF","SR830")
            return ValueAOFF
        # ==================================================================================
        #    
        # ==================================================================================                
        case "AOFF":
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","AOFF " + str(i),"SR830")
            SR830.write(b"AOFF " + str(i).encode() + b"\r")
            ValueAOFF = SR830.read_until(b"\r")
            ValueAOFF= ValueAOFF.decode("ascii", errors="replace").strip() 
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"),"Communication","SetValue","ValueAOFF","SR830")
            return ValueAOFF