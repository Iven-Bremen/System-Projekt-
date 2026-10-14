import tkinter as tk
from tkinter import ttk

def greeting():
    greeting = print("Hello there!")
    return greeting
def output():
    ttk.Label(root, text=entry.get()).pack(side='top', expand='true', fill='x')
def delete_entry():
    entry.delete(0, 'end')
#tk._test()
root = tk.Tk() #Hauptfenstererzeugung
root.title('My GUI') #GUI-Titel
root.geometry('300x300') #Startgröße
root.minsize(300, 300)
root.maxsize(600, 600)
#root.resizable(False, False) #nicht veränderbare größe mit true, nur eine einschränkung
style = ttk.Style()
style.theme_use('clam') #Damit Themes ignoriert werden

texe_var = tk.StringVar() #analog für int,double,boolean
texe_var.set("textt")

label1 = tk.Label(root, text='Hello World!', bg='blue', fg='orange')
label1.pack(side='top', expand='true', fill='both')  #Widget im Hauptfenster mit Positions und Größenzuweisung
label2 = ttk.Label(root, text='again')
label2["text"] = "Oops, I did it" #Alternativschreibweise 1
label2.pack(side='top', expand='true', fill='x')
label3 = ttk.Label(root)
label3.configure(textvariable=texe_var, font=('Courier'), padding=3) #Alternativschreibweise 2
label3.pack(side='bottom', expand='true', fi='both')

button1 = ttk.Button(root, text='Click me!',padding=10, command=greeting, state=tk.DISABLED)
button1.pack(side='bottom', expand='true', fill='x')

button2 = ttk.Button(root, text='Click me too!',padding=10, command=output)
button2.pack(side='bottom', expand='true', fill='x')

entf = ttk.Button(root, text='Enter text!',padding=10, command=delete_entry)
entf.pack(side='bottom')

alt_f4 = ttk.Button(root, text='close', command=root.destroy) #beendungsbutton
alt_f4.pack(side='bottom', expand='true', fill='x')

# menu button
menu_button = ttk.Menubutton(root, text='Menu Button')
menu_button.pack()

button_submenu = (tk.Menu(menu_button, tearoff=0))
button_submenu.add_command(label='entry', command=lambda : print(button_submenu_check.get()))
button_submenu_check = tk.BooleanVar()
button_submenu.add_checkbutton(label='check', onvalue=True, offvalue=False, variable=button_submenu_check)
menu_button.config(menu=button_submenu)

#for item in button1.keys():
 #   print(item, ': ', button1[item])

entry = ttk.Entry(root, width=40, justify='center')
entry.pack(side='top', expand='true', fill='x')
entry.insert(0, 'insert your text here:')

texe_var.set("again?") #aktualisierung geht später
root.mainloop() #Eventloop (hiernach folgt nichts an Codeabarbeitung)