/*
 * WaveRadar for Windows
 * Criado por Joaquim Pedro de Morais Filho - j360074@hotmail.com
 * (C) 2026 - Todos os direitos reservados. Licenca MIT.
 *
 * Radar de movimento por sensoriamento Wi-Fi (modo RSSI), sem hardware extra:
 * le a intensidade do sinal do seu Wi-Fi (netsh wlan show interfaces), aprende
 * o canal "silencioso" e transforma as variacoes causadas por pessoas em
 * movimento num radar ao vivo (varredura, blips, intensidade e Doppler).
 *
 * Compila com o csc do .NET Framework (C# 5):
 *   csc /target:winexe /out:WaveRadar.exe /r:System.Windows.Forms.dll /r:System.Drawing.dll WaveRadar.cs
 */
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Globalization;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;

namespace WaveRadar
{
    public class Blip
    {
        public double Angle;      // radianos
        public double Radius;     // 0..1
        public double Intensity;  // 0..1
        public double Age;        // segundos
    }

    public class RadarPanel : Control
    {
        public double SweepAngle = 0;
        public List<Blip> Blips = new List<Blip>();
        public List<double> History = new List<double>(); // sinal 0..100
        public int Signal = -1;
        public double Baseline = -1;
        public double Intensity = 0;
        public double FreqHz = 0;
        public string Status = "Iniciando...";
        public Color StatusColor = Color.Gray;

        private readonly Color cBg = Color.FromArgb(8, 14, 12);
        private readonly Color cGrid = Color.FromArgb(32, 70, 55);
        private readonly Color cGreen = Color.FromArgb(43, 255, 136);
        private readonly Color cGreenDim = Color.FromArgb(70, 43, 255, 136);

        public RadarPanel()
        {
            this.DoubleBuffered = true;
            this.SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer
                | ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            DoRender(e.Graphics, this.Width, this.Height);
        }

        public void DoRender(Graphics g, int w, int h)
        {
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.Clear(cBg);

            int radarSize = Math.Min(w, h - 86);
            int cx = w / 2;
            int cy = (h - 86) / 2 + 6;
            int R = radarSize / 2 - 14;
            if (R < 20) return;

            // grade: aneis
            using (Pen pg = new Pen(cGrid, 1f))
            {
                for (int i = 1; i <= 3; i++)
                {
                    int rr = R * i / 3;
                    g.DrawEllipse(pg, cx - rr, cy - rr, rr * 2, rr * 2);
                }
                g.DrawLine(pg, cx - R, cy, cx + R, cy);
                g.DrawLine(pg, cx, cy - R, cx, cy + R);
            }

            // setor da varredura (gradiente atras da linha)
            using (GraphicsPath path = new GraphicsPath())
            {
                float sweepDeg = (float)(SweepAngle * 180.0 / Math.PI);
                path.AddPie(cx - R, cy - R, R * 2, R * 2, sweepDeg - 40, 40);
                using (PathGradientBrush pgb = new PathGradientBrush(path))
                {
                    pgb.CenterColor = cGreenDim;
                    pgb.SurroundColors = new Color[] { Color.FromArgb(0, 43, 255, 136) };
                    pgb.CenterPoint = new PointF(cx, cy);
                    g.FillPath(pgb, path);
                }
                float lx = cx + (float)(R * Math.Cos(SweepAngle));
                float ly = cy + (float)(R * Math.Sin(SweepAngle));
                using (Pen ps = new Pen(cGreen, 2f))
                    g.DrawLine(ps, cx, cy, lx, ly);
            }

            // blips
            foreach (Blip b in Blips)
            {
                double fade = Math.Max(0, 1.0 - b.Age / 3.5);
                if (fade <= 0) continue;
                float bx = cx + (float)(R * b.Radius * Math.Cos(b.Angle));
                float by = cy + (float)(R * b.Radius * Math.Sin(b.Angle));
                int sz = (int)(6 + 16 * b.Intensity);
                int alpha = (int)(230 * fade);
                using (SolidBrush sb = new SolidBrush(Color.FromArgb(Math.Max(0, Math.Min(255, alpha)), cGreen)))
                    g.FillEllipse(sb, bx - sz / 2, by - sz / 2, sz, sz);
                using (SolidBrush sb2 = new SolidBrush(Color.FromArgb(Math.Max(0, Math.Min(90, alpha / 2)), cGreen)))
                    g.FillEllipse(sb2, bx - sz, by - sz, sz * 2, sz * 2);
            }

            // centro
            using (SolidBrush c = new SolidBrush(cGreen))
                g.FillEllipse(c, cx - 3, cy - 3, 6, 6);

            // historico do sinal (faixa inferior)
            int baseY = h - 70;
            using (Pen pg = new Pen(cGrid, 1f))
                g.DrawLine(pg, 16, baseY, w - 16, baseY);
            if (History.Count > 1)
            {
                int n = History.Count;
                float stepx = (float)(w - 32) / Math.Max(1, n - 1);
                using (Pen pl = new Pen(cGreen, 1.5f))
                {
                    PointF prev = PointF.Empty;
                    for (int i = 0; i < n; i++)
                    {
                        float x = 16 + stepx * i;
                        float y = baseY - (float)(History[i] * 0.5); // 0..100 -> 0..50px
                        PointF cur = new PointF(x, y);
                        if (i > 0) g.DrawLine(pl, prev, cur);
                        prev = cur;
                    }
                }
            }

            // textos
            using (Font f = new Font("Consolas", 10f))
            using (Font fb = new Font("Consolas", 13f, FontStyle.Bold))
            using (SolidBrush white = new SolidBrush(Color.FromArgb(230, 236, 255)))
            using (SolidBrush st = new SolidBrush(StatusColor))
            {
                g.DrawString(Status, fb, st, 16, h - 60);
                string line1 = string.Format(CultureInfo.InvariantCulture,
                    "Sinal: {0}%   Base: {1}   Intensidade: {2:0}%   Doppler: {3:0.0} Hz",
                    Signal >= 0 ? Signal.ToString() : "--",
                    Baseline >= 0 ? Baseline.ToString("0") : "--",
                    Intensity * 100, FreqHz);
                g.DrawString(line1, f, white, 16, h - 36);
                g.DrawString("WaveRadar  ·  Joaquim Pedro de Morais Filho", f,
                    new SolidBrush(Color.FromArgb(120, 200, 210, 230)), w - 360, 10);
            }
        }
    }

    public class MainForm : Form
    {
        private RadarPanel radar;
        private TrackBar sens;
        private Button btStart, btCal;
        private Label lblSens;
        private System.Windows.Forms.Timer ui;
        private Thread sensing;
        private volatile bool running = false;

        // estado de sensoriamento
        private readonly object sync = new object();
        private int curSignal = -1;
        private double baseline = -1, noise = 2;
        private readonly List<double> calib = new List<double>();
        private DateTime calibStart;
        private bool calibrating = true;
        private double prevSignal = -1;
        private readonly LinkedList<double> osc = new LinkedList<double>(); // (sinal - media lenta)
        private double slowMean = -1;

        public MainForm()
        {
            this.Text = "WaveRadar — Joaquim Pedro de Morais Filho";
            this.BackColor = Color.FromArgb(8, 14, 12);
            this.ClientSize = new Size(900, 620);
            this.MinimumSize = new Size(680, 520);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.Font = new Font("Segoe UI", 9f);

            radar = new RadarPanel();
            radar.Location = new Point(12, 54);
            radar.Size = new Size(876, 554);
            radar.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            this.Controls.Add(radar);

            btStart = MakeButton("▶  Iniciar", 12, 12, 120, Color.FromArgb(31, 191, 102));
            btStart.Click += delegate { Toggle(); };
            this.Controls.Add(btStart);

            btCal = MakeButton("Recalibrar", 140, 12, 110, Color.FromArgb(57, 72, 103));
            btCal.Click += delegate { Recalibrate(); };
            this.Controls.Add(btCal);

            lblSens = new Label();
            lblSens.Text = "Sensibilidade";
            lblSens.ForeColor = Color.FromArgb(154, 166, 192);
            lblSens.AutoSize = true;
            lblSens.Location = new Point(285, 18);
            this.Controls.Add(lblSens);

            sens = new TrackBar();
            sens.Minimum = 1; sens.Maximum = 10; sens.Value = 5;
            sens.TickStyle = TickStyle.None;
            sens.Location = new Point(378, 10);
            sens.Width = 160;
            this.Controls.Add(sens);

            ui = new System.Windows.Forms.Timer();
            ui.Interval = 33; // ~30 fps
            ui.Tick += delegate { Animate(); };
            ui.Start();

            this.FormClosing += delegate { running = false; };
            Recalibrate();
            Start();
        }

        private Button MakeButton(string text, int x, int y, int w, Color bg)
        {
            Button b = new Button();
            b.Text = text; b.Location = new Point(x, y); b.Size = new Size(w, 32);
            b.FlatStyle = FlatStyle.Flat; b.BackColor = bg; b.ForeColor = Color.White;
            b.FlatAppearance.BorderSize = 0; b.Font = new Font("Segoe UI", 9f, FontStyle.Bold);
            return b;
        }

        private void Toggle() { if (running) Stop(); else Start(); }

        private void Start()
        {
            if (running) return;
            running = true;
            btStart.Text = "■  Parar";
            btStart.BackColor = Color.FromArgb(204, 60, 60);
            sensing = new Thread(SenseLoop);
            sensing.IsBackground = true;
            sensing.Start();
        }

        private void Stop()
        {
            running = false;
            btStart.Text = "▶  Iniciar";
            btStart.BackColor = Color.FromArgb(31, 191, 102);
        }

        private void Recalibrate()
        {
            lock (sync)
            {
                calib.Clear();
                calibrating = true;
                calibStart = DateTime.Now;
                baseline = -1;
                osc.Clear();
                slowMean = -1;
                prevSignal = -1;
            }
        }

        private void SenseLoop()
        {
            while (running)
            {
                int sig = ReadSignal();
                DateTime now = DateTime.Now;
                lock (sync)
                {
                    curSignal = sig;
                    if (sig >= 0)
                    {
                        // media lenta (para o oscilador do Doppler)
                        slowMean = (slowMean < 0) ? sig : slowMean * 0.9 + sig * 0.1;
                        double o = sig - slowMean;
                        osc.AddLast(o);
                        while (osc.Count > 40) osc.RemoveFirst(); // ~40 amostras

                        if (calibrating)
                        {
                            calib.Add(sig);
                            if ((now - calibStart).TotalSeconds >= 6 && calib.Count >= 12)
                            {
                                double m = 0; foreach (double v in calib) m += v; m /= calib.Count;
                                double s = 0; foreach (double v in calib) s += (v - m) * (v - m);
                                s = Math.Sqrt(s / Math.Max(1, calib.Count));
                                baseline = m;
                                noise = Math.Max(1.0, s);
                                calibrating = false;
                            }
                        }
                        prevSignal = sig;
                    }
                }
                Thread.Sleep(280);
            }
        }

        private static readonly Regex RxPct = new Regex(@"(\d+)\s*%", RegexOptions.Compiled);

        private int ReadSignal()
        {
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo("netsh", "wlan show interfaces");
                psi.RedirectStandardOutput = true;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                psi.StandardOutputEncoding = System.Text.Encoding.UTF8;
                Process p = Process.Start(psi);
                string outp = p.StandardOutput.ReadToEnd();
                p.WaitForExit(2000);
                Match m = RxPct.Match(outp);
                if (m.Success)
                {
                    int v = int.Parse(m.Groups[1].Value);
                    if (v >= 0 && v <= 100) return v;
                }
            }
            catch { }
            return -1;
        }

        private void Animate()
        {
            double sweepSpeed = 2.2; // rad/s
            radar.SweepAngle += sweepSpeed * (ui.Interval / 1000.0);
            if (radar.SweepAngle > Math.PI * 2) radar.SweepAngle -= Math.PI * 2;

            int sig; double b, nz; bool cal; double sMean;
            double[] oscArr;
            lock (sync)
            {
                sig = curSignal; b = baseline; nz = noise; cal = calibrating; sMean = slowMean;
                oscArr = new double[osc.Count]; osc.CopyTo(oscArr, 0);
            }

            // historico
            if (sig >= 0)
            {
                radar.History.Add(sig);
                while (radar.History.Count > 220) radar.History.RemoveAt(0);
            }
            radar.Signal = sig;
            radar.Baseline = b;

            // intensidade de movimento
            double intensity = 0;
            double sensF = sens.Value / 5.0; // 0.2 .. 2.0
            if (!cal && b >= 0 && sig >= 0)
            {
                double dev = Math.Abs(sig - b);
                double over = dev - nz; // acima do ruido
                intensity = Math.Max(0, over) / (12.0 / sensF);
                // variancia recente tambem contribui
                double va = 0; if (oscArr.Length > 1) { double mm = 0; foreach (double v in oscArr) mm += v; mm /= oscArr.Length; foreach (double v in oscArr) va += (v - mm) * (v - mm); va = Math.Sqrt(va / oscArr.Length); }
                intensity += (va / (8.0 / sensF));
                if (intensity > 1) intensity = 1;
            }
            radar.Intensity = intensity;

            // frequencia (Doppler) via zero-crossings do oscilador
            double freq = 0;
            if (oscArr.Length > 4)
            {
                int zc = 0;
                for (int i = 1; i < oscArr.Length; i++)
                    if ((oscArr[i - 1] <= 0 && oscArr[i] > 0) || (oscArr[i - 1] >= 0 && oscArr[i] < 0)) zc++;
                double windowSec = oscArr.Length * 0.28;
                freq = (zc / 2.0) / Math.Max(0.5, windowSec);
                if (freq > 6) freq = 6;
            }
            radar.FreqHz = freq;

            // status
            if (cal)
            {
                int left = (int)Math.Ceiling(6 - (DateTime.Now - calibStart).TotalSeconds);
                radar.Status = "Calibrando o canal silencioso... " + Math.Max(0, left) + "s";
                radar.StatusColor = Color.FromArgb(255, 200, 60);
            }
            else if (sig < 0)
            {
                radar.Status = "Sem Wi-Fi conectado";
                radar.StatusColor = Color.FromArgb(204, 80, 80);
            }
            else if (intensity > 0.12)
            {
                radar.Status = "● MOVIMENTO DETECTADO";
                radar.StatusColor = Color.FromArgb(255, 90, 90);
                // adiciona blip na direcao da varredura
                Blip bl = new Blip();
                bl.Angle = radar.SweepAngle;
                bl.Radius = 0.35 + 0.6 * intensity;
                bl.Intensity = intensity;
                bl.Age = 0;
                radar.Blips.Add(bl);
            }
            else
            {
                radar.Status = "Silêncio — sem movimento";
                radar.StatusColor = Color.FromArgb(43, 255, 136);
            }

            // envelhece blips
            double dt = ui.Interval / 1000.0;
            for (int i = radar.Blips.Count - 1; i >= 0; i--)
            {
                radar.Blips[i].Age += dt;
                if (radar.Blips[i].Age > 3.6) radar.Blips.RemoveAt(i);
            }

            radar.Invalidate();
        }

        [STAThread]
        public static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            if (args != null && args.Length >= 2 && args[0] == "--shot")
            {
                RenderShot(args[1]);
                return;
            }
            Application.Run(new MainForm());
        }

        // Renderiza um screenshot do app (cena de demonstracao) para a loja.
        private static void RenderShot(string path)
        {
            int W = 900, H = 620;
            using (Bitmap bmp = new Bitmap(W, H))
            using (Graphics g = Graphics.FromImage(bmp))
            {
                g.SmoothingMode = SmoothingMode.AntiAlias;
                g.Clear(Color.FromArgb(8, 14, 12));

                // radar (renderizado em bitmap proprio e composto)
                RadarPanel rp = new RadarPanel();
                rp.Signal = 78; rp.Baseline = 92; rp.Intensity = 0.62; rp.FreqHz = 1.8;
                rp.Status = "● MOVIMENTO DETECTADO"; rp.StatusColor = Color.FromArgb(255, 90, 90);
                rp.SweepAngle = 0.95;
                double[] ang = { 0.4, 1.6, 2.7, 3.9, 5.2 };
                double[] rad = { 0.55, 0.78, 0.40, 0.66, 0.85 };
                double[] inten = { 0.6, 0.9, 0.4, 0.7, 0.5 };
                for (int i = 0; i < ang.Length; i++)
                {
                    Blip bl = new Blip();
                    bl.Angle = ang[i]; bl.Radius = rad[i]; bl.Intensity = inten[i]; bl.Age = i * 0.25;
                    rp.Blips.Add(bl);
                }
                for (int i = 0; i < 210; i++)
                    rp.History.Add(88 + 10 * Math.Sin(i * 0.25) + ((i % 19 < 3) ? -16 : 0));
                using (Bitmap rbmp = new Bitmap(876, 554))
                using (Graphics rg = Graphics.FromImage(rbmp))
                {
                    rg.SmoothingMode = SmoothingMode.AntiAlias;
                    rp.DoRender(rg, 876, 554);
                    g.DrawImage(rbmp, 12, 54);
                }

                // barra superior (botoes + sensibilidade)
                using (SolidBrush b1 = new SolidBrush(Color.FromArgb(204, 60, 60)))
                    g.FillRectangle(b1, 12, 12, 120, 32);
                using (SolidBrush b2 = new SolidBrush(Color.FromArgb(57, 72, 103)))
                    g.FillRectangle(b2, 140, 12, 110, 32);
                using (Font fb = new Font("Segoe UI", 9f, FontStyle.Bold))
                using (Font f = new Font("Segoe UI", 9f))
                {
                    g.DrawString("■  Parar", fb, Brushes.White, 32, 20);
                    g.DrawString("Recalibrar", fb, Brushes.White, 157, 20);
                    g.DrawString("Sensibilidade", f, new SolidBrush(Color.FromArgb(154, 166, 192)), 285, 18);
                    using (Pen ps = new Pen(Color.FromArgb(90, 110, 140), 3f))
                        g.DrawLine(ps, 378, 26, 538, 26);
                    using (SolidBrush k = new SolidBrush(Color.FromArgb(31, 191, 102)))
                        g.FillEllipse(k, 452, 20, 12, 12);
                }
                bmp.Save(path, System.Drawing.Imaging.ImageFormat.Png);
            }
        }
    }
}
