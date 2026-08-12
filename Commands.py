import serial
import time

def getValue(Init,COM,Command,i,j,k):

    match Command:
    # ==================================================================================    
    # Query the value of Aux Input i (1,2,3,4)
    # ==================================================================================
        case "OAUX1":
            Init.write(b"OAUX ? 1\r")
            ValueOAUX1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()
        case "OAUX2":
            Init.write(b"OAUX ? 2\r")
            ValueOAUX2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()
        case "OAUX3":
            Init.write(b"OAUX ? 3\r")
            ValueOAUX3 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()            
        case "OAUX4":
            Init.write(b"OAUX ? 4\r")
            ValueOAUX4 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()        
    # ==================================================================================
    # Query the value of X (1), Y (2), R (3) or q (4). Returns ASCII floating point value
    # ==================================================================================                     
        case "OUTP1":
            Init.write(b"OUTP? 1\r")
            ValueOUTP1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()     
        case "OUTP2":
            Init.write(b"OUTP? 2\r")
            ValueOUTP2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()                 
        case "OUTP3":
            Init.write(b"OUTP? 3\r")
            ValueOUTP3 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()                 
        case "OUTP4":
            Init.write(b"OUTP? 4\r")
            ValueOUTP4 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()
    # ==================================================================================
    #  Query the value of Display i (1,2). Returns ASCII floating point value.
    # ==================================================================================                     
        case "OUTR1":
            Init.write(b"OUTR? 1\r")
            ValueOUTR1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()     
        case "OUTR2":
            Init.write(b"OUTR? 2\r")
            ValueOUTR2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()                 
    # ==================================================================================
    #   Query the value of 2 thru 6 paramters at once.
    # ==================================================================================                     
        case "SNAP":
            Init.write(b"SNAP?" + str(i).encode() + b"," + str(j).encode() + b"\r")
            ValueSNAP = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()     
    # ==================================================================================
    #   Query the value of Aux Input i (1,2,3,4). Returns ASCII floating point value
    # ==================================================================================                     
        case "OAUX1":
            Init.write(b"OAUX? 1\r")
            ValueOAUX1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()      
        case "OAUX2":
            Init.write(b"OAUX? 2\r")
            ValueOAUX2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()      
        case "OAUX3":
            Init.write(b"OAUX? 3\r")
            ValueOAUX3 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()      
        case "OAUX4":
            Init.write(b"OAUX? 4\r")
            ValueOAUX4 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()                                                   
    # ==================================================================================
    #   Query the number of points stored in Display buffer.
    # ==================================================================================                     
        case "SPTS":
            Init.write(b"SPTS?\r")
            ValueSPTS = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()    
    # ==================================================================================
    #   Read k>=1 points starting at bin j>=0 from Display i (1,2) buffer in ASCII floating point
    # ==================================================================================                     
        case "TRCA1":
            Init.write(b"TRCA? 1," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCA1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()                       
        case "TRCA2":
            Init.write(b"TRCA? 2," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCA2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()        
    # ==================================================================================
    #    Read k>=1 points starting at bin j>=0 from Display i (1,2) buffer in IEEE binary floating point.
    # ==================================================================================                     
        case "TRCB1":
            Init.write(b"TRCB? 1," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCB1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()                       
        case "TRCB2":
            Init.write(b"TRCB? 2," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCB2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()                   
    # ==================================================================================
    #    Read k>=1 points starting at bin j>=0 from Display i (1,2) buffer in non-normalized binary floatingpoint.
    # ==================================================================================                     
        case "TRCL1":
            Init.write(b"TRCL? 1," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCL1 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()                       
        case "TRCL2":
            Init.write(b"TRCL? 2," + str(j).encode() + b"," + str(k).encode() + b"\r")
            ValueTRCL2 = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()   
    # ==================================================================================
    #     Read the SR830 device identification string
    # ==================================================================================                     
        case "IDN?":
            Init.write(b"IDN?\r")
            ValueIDN = Init.readuntil(b"\r").decode("ascii", errors="replace").strip()                         