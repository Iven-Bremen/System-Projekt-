import Updatete_KOM
import Log

Current_Phas = Updatete_KOM.SerialChannel.write("PHAS")
Log.LogMassage("PHAS", Current_Phas, "Communication", "PHAS")

