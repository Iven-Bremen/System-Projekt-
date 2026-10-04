# Ersatz fuer starte_messunsicherheit_analyse() in GUI.py
# (parse_ptr_log_csv wird dafuer nicht mehr gebraucht)

def starte_messunsicherheit_analyse():
    """Run Uncertainty: Typ-A-Auswertung (Referenz + Probe) und Fit durch die Mittelwerte."""
    global fig_pvf, canvas_pvf

    ftypes = [("CSV Files", "*.csv"), ("All files", "*.*")]

    # 1. Referenz-Dateien (mehrere Sweeps = Mehrfachauswahl mit Strg/Shift)
    ref_paths = filedialog.askopenfilenames(
        title="Referenzmessung(en) auswählen (unnitriert)", filetypes=ftypes)
    if not ref_paths:
        return

    # 2. Proben-Dateien
    probe_paths = filedialog.askopenfilenames(
        title="Probenmessung(en) auswählen (nitriert)", filetypes=ftypes)
    if not probe_paths:
        return

    # 3. Auswertung: das Modul liest die SNAP-Logs selbst ein
    try:
        out = SWP_SM_v2.start_Messunsicherheit_Fit(list(ref_paths), list(probe_paths))
        res_ref, res_probe, fit = out["ref"], out["probe"], out["fit"]
    except Exception as e:
        messagebox.showerror("Fehler bei Messunsicherheit", f"{type(e).__name__}: {e}")
        return

    if min(res_ref["n"].max(), res_probe["n"].max()) < 2:
        messagebox.showwarning(
            "Zu wenige Messwiederholungen",
            "Pro Frequenz liegt nur ein Messwert vor – Streuung und u_A sind nicht "
            "berechenbar. Bitte mehrere Sweeps (mehrere Dateien) auswählen.")

    # 4. Plot
    try:
        if fig_pvf is None:
            fig_pvf = plt.Figure(figsize=(6, 7), dpi=100)
        else:
            fig_pvf.clf()

        ax1 = fig_pvf.add_subplot(311)
        ax2 = fig_pvf.add_subplot(312)
        ax3 = fig_pvf.add_subplot(313)

        for res, name, col in ((res_ref, "Referenz", "tab:blue"),
                               (res_probe, "Probe", "tab:orange")):
            ax1.plot(res["raw_freq"], res["raw_phase"], ".", color=col, alpha=0.25, ms=4)
            ax1.errorbar(res["freq"], res["phase_mean"], yerr=res["phase_std"],
                         fmt="o-", color=col, capsize=3, ms=4, label=f"{name}: Mittelwert ± s")
        ax1.set_xscale("log")
        ax1.set_xlabel("Frequenz in Hz")
        ax1.set_ylabel("Phase in °")
        ax1.set_title("Einzelwerte, Mittelwert ± Streuung s")
        ax1.grid(True, which="both", linestyle="--", alpha=0.5)
        ax1.legend(loc="best")

        x = np.sqrt(2 * np.pi * fit["freq"])
        x_fine = np.sqrt(2 * np.pi * fit["freq_fine"])
        ax2.errorbar(x, fit["Phi"], yerr=fit["u_phi"], fmt="o", capsize=3,
                     color="tab:green", label=r"$\Phi$ ± $u_\Phi$")
        ax2.plot(x_fine, fit["Phi_fit_curve"], "--", color="k", label="Fit")
        ax2.set_xlabel(r"$\sqrt{\omega}$ in $\sqrt{Hz}$")
        ax2.set_ylabel("Φ in °")
        ax2.set_title(f"d = {fit['d_fit_um']:.2f} ± {fit['d_err_um']:.2f} µm,  "
                      f"k_L = {fit['kL_fit']:.2f} ± {fit['kL_err']:.2f} W/(m·K)")
        ax2.grid(True, linestyle="--", alpha=0.5)
        ax2.legend(loc="best")

        ax3.errorbar(x, fit["residual"], yerr=fit["u_phi"], fmt="o", capsize=3, color="tab:green")
        ax3.axhline(0, color="k", lw=1)
        ax3.set_xlabel(r"$\sqrt{\omega}$ in $\sqrt{Hz}$")
        ax3.set_ylabel("Mittelwert − Fit in °")
        ax3.grid(True, linestyle="--", alpha=0.5)

        fig_pvf.tight_layout()

        if canvas_pvf is None:
            canvas_pvf = FigureCanvasTkAgg(fig_pvf, master=frame_plot_pvf)
            canvas_pvf.get_tk_widget().pack(fill="both", expand=True)
        canvas_pvf.draw()          # <- fehlte in der alten Version
    except Exception as e:
        messagebox.showerror("Plot-Fehler", f"{type(e).__name__}: {e}")
