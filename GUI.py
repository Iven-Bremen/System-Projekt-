import tkinter as tk
#tk._test()
root = tk.Tk() #Hauptfenstererzeugung
root.title('My GUI') #GUI-Titel
root.geometry('300x300') #Startgröße
root.minsize(300, 300)
root.maxsize(600, 600)
#root.resizable(False, False) #nicht veränderbare größe mit true, nur eine einschränkung

label1 = tk.Label(root, text='Hello World!')
label1.pack()  #Widget im Hauptfenster

root.mainloop() #Eventloop (hiernach folgt nichts an Codeabarbeitung)