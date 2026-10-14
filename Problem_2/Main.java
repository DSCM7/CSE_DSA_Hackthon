import java.awt.*;
import java.awt.event.*;
import java.util.*;
import java.util.List;
import java.util.function.Supplier;
import javax.swing.*;
import javax.swing.border.EmptyBorder;
import javax.swing.border.LineBorder;
import javax.swing.table.*;

/**
 * Problem 2 - Closest Pair of Points: comparative analysis.
 *
 * stdin : N
 * stdout : line 1 Brute-Force -> distance (6 dp) + the two points
 * line 2 Divide-and-Conquer -> distance (6 dp) + the two points
 * line 3 execution time of each algorithm in ms
 * GUI : overview, brute force, divide & conquer (split line + 2d strip),
 * recursion animation, running-time graph, verification suite.
 *
 * Optional argument: a numeric seed to reproduce a run (java Main 12345)
 */
public class Main {

    // =====================================================================
    // MODEL
    // =====================================================================
    static final class P {
        final double x, y;
        int rank; // position in the x-sorted order (used by the animation)

        P(double x, double y) {
            this.x = x;
            this.y = y;
        }
    }

    static final class Result {
        final double d2; // squared distance
        final P a, b; // a <= b (by x, then y) so equal pairs print identically

        Result(double d2, P p, P q) {
            this.d2 = d2;
            if (p.x > q.x || (p.x == q.x && p.y > q.y)) {
                a = q;
                b = p;
            } else {
                a = p;
                b = q;
            }
        }

        double dist() {
            return Math.sqrt(d2);
        }
    }

    static final class Bench {
        final int n;
        final double bruteMs, dcMs;

        Bench(int n, double bruteMs, double dcMs) {
            this.n = n;
            this.bruteMs = bruteMs;
            this.dcMs = dcMs;
        }
    }

    // =====================================================================
    // ALGORITHMS
    // =====================================================================
    static final Comparator<P> BY_X = (u, v) -> u.x != v.x ? Double.compare(u.x, v.x) : Double.compare(u.y, v.y);
    static final Comparator<P> BY_Y = (u, v) -> u.y != v.y ? Double.compare(u.y, v.y) : Double.compare(u.x, v.x);

    static double d2(P u, P v) {
        double dx = u.x - v.x, dy = u.y - v.y;
        return dx * dx + dy * dy;
    }

    /** Brute force on a[lo..hi). Returns null when fewer than 2 points. */
    static Result brute(P[] a, int lo, int hi) {
        if (hi - lo < 2)
            return null;
        double best = Double.POSITIVE_INFINITY;
        P p = null, q = null;
        for (int i = lo; i < hi; i++) {
            P u = a[i];
            for (int j = i + 1; j < hi; j++) {
                double dx = u.x - a[j].x, dy = u.y - a[j].y;
                double d = dx * dx + dy * dy;
                if (d < best) {
                    best = d;
                    p = u;
                    q = a[j];
                }
            }
        }
        return new Result(best, p, q);
    }

    static Result bruteForce(P[] pts) {
        return brute(pts, 0, pts.length);
    }

    /** Divide and conquer, O(N log N). Returns null when fewer than 2 points. */
    static Result divideConquer(P[] pts) {
        int n = pts.length;
        if (n < 2)
            return null;
        P[] a = pts.clone();
        Arrays.sort(a, BY_X);
        return rec(a, new P[n], 0, n);
    }

    /** a[lo..hi) is x-sorted on entry and y-sorted on exit (merge sort style). */
    static Result rec(P[] a, P[] t, int lo, int hi) {
        int n = hi - lo;
        if (n <= 3) {
            Result r = brute(a, lo, hi);
            for (int i = lo + 1; i < hi; i++) { // insertion sort by y
                P k = a[i];
                int j = i - 1;
                while (j >= lo && BY_Y.compare(a[j], k) > 0) {
                    a[j + 1] = a[j];
                    j--;
                }
                a[j + 1] = k;
            }
            return r;
        }
        int mid = (lo + hi) >>> 1;
        double midX = a[mid].x;
        Result l = rec(a, t, lo, mid), r = rec(a, t, mid, hi);
        Result best = l.d2 <= r.d2 ? l : r;

        int i = lo, j = mid, k = lo; // merge by y
        while (i < mid && j < hi)
            t[k++] = BY_Y.compare(a[i], a[j]) <= 0 ? a[i++] : a[j++];
        while (i < mid)
            t[k++] = a[i++];
        while (j < hi)
            t[k++] = a[j++];
        System.arraycopy(t, lo, a, lo, n);

        int m = 0; // strip |x - midX| < d
        for (int x = lo; x < hi; x++) {
            double dx = a[x].x - midX;
            if (dx * dx < best.d2)
                t[lo + m++] = a[x];
        }
        for (i = 0; i < m; i++) {
            P u = t[lo + i];
            for (j = i + 1; j < m; j++) {
                P v = t[lo + j];
                double dy = v.y - u.y;
                if (dy * dy >= best.d2)
                    break;
                double dx = u.x - v.x, d = dx * dx + dy * dy;
                if (d < best.d2)
                    best = new Result(d, u, v);
            }
        }
        return best;
    }

    // =====================================================================
    // DATA, TIMING, BENCHMARK
    // =====================================================================
    static int rangeFor(int n) {
        return (int) Math.min(20_000_000L, Math.max(1000L, 10L * n));
    }

    static P[] makePoints(int n, long seed, int range) {
        Random rng = new Random(seed);
        P[] p = new P[n];
        for (int i = 0; i < n; i++)
            p[i] = new P(rng.nextInt(range + 1), rng.nextInt(range + 1));
        return p;
    }

    static volatile Object sink; // keeps the JIT from discarding the work

    static double timeMs(Supplier<Result> task, int reps) {
        double best = Double.POSITIVE_INFINITY;
        for (int r = 0; r < reps; r++) {
            long s = System.nanoTime();
            Result x = task.get();
            long e = System.nanoTime();
            sink = x;
            best = Math.min(best, (e - s) / 1e6);
        }
        return best;
    }

    static void warmUp() {
        P[] w = makePoints(1500, 7, 1000);
        for (int i = 0; i < 15; i++) {
            sink = bruteForce(w);
            sink = divideConquer(w);
        }
    }

    static List<Bench> benchmark() {
        int[] sizes = { 100, 250, 500, 1000, 2000, 4000, 8000, 12000, 16000 };
        List<Bench> out = new ArrayList<>();
        for (int n : sizes) {
            P[] pts = makePoints(n, 9000L + n, rangeFor(n));
            int reps = n <= 1000 ? 9 : n <= 4000 ? 5 : 3;
            out.add(new Bench(n, timeMs(() -> bruteForce(pts), reps),
                    timeMs(() -> divideConquer(pts), reps)));
        }
        return out;
    }

    // ---------- formatting ----------
    static String fmt(double v) {
        return v == Math.rint(v) ? String.valueOf((long) v) : String.format(Locale.US, "%.3f", v);
    }

    static String pt(P p) {
        return "(" + fmt(p.x) + ", " + fmt(p.y) + ")";
    }

    static String line(Result r) {
        return String.format(Locale.US, "%.6f %s %s", r.dist(), pt(r.a), pt(r.b));
    }

    // =====================================================================
    // ANIMATION MODEL (records the recursion of divide & conquer)
    // =====================================================================
    static final int SPLIT = 0, BASE = 1, MERGE = 2, DONE = 3;

    static final class Step {
        int kind, lo, hi, mid = -1;
        double midX = Double.NaN, d = Double.NaN;
        Result pair;
        double[] anc = new double[0];
        Set<P> strip = Collections.emptySet();
        String title = "", text = "";
    }

    static final class Anim {
        final List<Step> steps = new ArrayList<>();
        final P[] px;
        final int leaf;
        Step rootMerge;

        Anim(P[] pts) {
            px = pts.clone();
            Arrays.sort(px, BY_X);
            for (int i = 0; i < px.length; i++)
                px[i].rank = i;
            leaf = Math.max(3, px.length / 16);
            Result res = rec(0, px.length, new double[0]);
            Step s = new Step();
            s.kind = DONE;
            s.lo = 0;
            s.hi = px.length;
            s.pair = res;
            s.title = "Done";
            s.text = String.format(Locale.US,
                    "Closest pair found: %s - %s, d = %.6f", pt(res.a), pt(res.b), res.dist());
            steps.add(s);
        }

        Result rec(int lo, int hi, double[] anc) {
            int n = hi - lo;
            if (n <= leaf) {
                Result r = brute(px, lo, hi);
                Step s = new Step();
                s.kind = BASE;
                s.lo = lo;
                s.hi = hi;
                s.pair = r;
                s.anc = anc;
                s.title = "Base case";
                s.text = String.format(Locale.US,
                        "%d points are small enough: solve them directly (d = %.3f).", n, r.dist());
                steps.add(s);
                return r;
            }
            int mid = (lo + hi) >>> 1;
            double midX = px[mid].x;
            Step sp = new Step();
            sp.kind = SPLIT;
            sp.lo = lo;
            sp.hi = hi;
            sp.mid = mid;
            sp.midX = midX;
            sp.anc = anc;
            sp.title = "Divide";
            sp.text = String.format(Locale.US, "Split %d points at x = %s into %d (left) and %d (right).",
                    n, fmt(midX), mid - lo, hi - mid);
            steps.add(sp);

            double[] next = Arrays.copyOf(anc, anc.length + 1);
            next[anc.length] = midX;
            Result l = rec(lo, mid, next), r = rec(mid, hi, next);
            Result best = l.d2 <= r.d2 ? l : r;
            double d0 = best.dist();

            P[] ys = Arrays.copyOfRange(px, lo, hi);
            Arrays.sort(ys, BY_Y);
            List<P> strip = new ArrayList<>();
            for (P p : ys) {
                double dx = p.x - midX;
                if (dx * dx < best.d2)
                    strip.add(p);
            }
            Result improved = best;
            for (int i = 0; i < strip.size(); i++) {
                for (int j = i + 1; j < strip.size(); j++) {
                    double dy = strip.get(j).y - strip.get(i).y;
                    if (dy * dy >= improved.d2)
                        break;
                    double d = d2(strip.get(i), strip.get(j));
                    if (d < improved.d2)
                        improved = new Result(d, strip.get(i), strip.get(j));
                }
            }
            Step m = new Step();
            m.kind = MERGE;
            m.lo = lo;
            m.hi = hi;
            m.mid = mid;
            m.midX = midX;
            m.d = d0;
            m.pair = improved;
            m.anc = anc;
            m.strip = new HashSet<>(strip);
            m.title = "Combine";
            m.text = String.format(Locale.US,
                    "d = min(left, right) = %.3f. The strip of width 2d holds %d point(s); %s",
                    d0, strip.size(), improved != best
                            ? String.format(Locale.US, "a closer pair crosses the line: d = %.3f.", improved.dist())
                            : "no closer pair crosses the line.");
            steps.add(m);
            if (lo == 0 && hi == px.length)
                rootMerge = m;
            return improved;
        }
    }

    // =====================================================================
    // THEME + SMALL UI HELPERS
    // =====================================================================
    static final Color BG = new Color(0x0b1220), PANEL = new Color(0x111a2e), PLOTBG = new Color(0x0d1527),
            CARD = new Color(0x17223b), CARD2 = new Color(0x22304f), GRID = new Color(0x1f2c47),
            AXIS = new Color(0x3b4a68), TEXT = new Color(0xe6ebf5), MUTED = new Color(0x8b98b0),
            BRUTE = new Color(0xff5d6c), DC = new Color(0x38bdf8), SPLITC = new Color(0x4ade80),
            STRIPC = new Color(0xfbbf24), POINT = new Color(0xa3b3d1, false), AMBER = new Color(0xf472b6),
            TEAL = new Color(0x2dd4bf), PURPLE = new Color(0xc084fc), ACCENT = new Color(0x3b82f6),
            DIM = new Color(100, 116, 139, 70), OK = new Color(0x34d399);

    static Color al(Color c, int a) {
        return new Color(c.getRed(), c.getGreen(), c.getBlue(), a);
    }

    static Font font(int style, int size) {
        return new Font("Segoe UI", style, size);
    }

    static Graphics2D aa(Graphics gr) {
        Graphics2D g = (Graphics2D) gr.create();
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_STROKE_CONTROL, RenderingHints.VALUE_STROKE_PURE);
        return g;
    }

    static final BasicStroke DASH = new BasicStroke(2f, BasicStroke.CAP_BUTT, BasicStroke.JOIN_MITER,
            10f, new float[] { 8f, 6f }, 0f);

    static double niceStep(double raw) {
        if (raw <= 0 || Double.isNaN(raw))
            return 1;
        double p = Math.pow(10, Math.floor(Math.log10(raw)));
        double f = raw / p;
        return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p;
    }

    static String tick(double v, double step) {
        if (step >= 1)
            return String.valueOf(Math.round(v));
        int dec = (int) Math.ceil(-Math.log10(step));
        return String.format(Locale.US, "%." + dec + "f", v);
    }

    static void pill(Graphics2D g, String s, int x, int y, Color c, Rectangle clip) {
        g.setFont(font(Font.BOLD, 12));
        FontMetrics fm = g.getFontMetrics();
        int w = fm.stringWidth(s) + 18, h = fm.getHeight() + 6;
        x = Math.max(clip.x + 4, Math.min(x, clip.x + clip.width - w - 4));
        y = Math.max(clip.y + 4, Math.min(y, clip.y + clip.height - h - 4));
        g.setColor(al(CARD, 240));
        g.fillRoundRect(x, y, w, h, 12, 12);
        g.setColor(c);
        g.setStroke(new BasicStroke(1.2f));
        g.drawRoundRect(x, y, w, h, 12, 12);
        g.setColor(TEXT);
        g.drawString(s, x + 9, y + h - fm.getDescent() - 3);
    }

    static final class FlatButton extends JButton {
        boolean active, hover;

        FlatButton(String t) {
            super(t);
            setContentAreaFilled(false);
            setBorderPainted(false);
            setFocusPainted(false);
            setOpaque(false);
            setForeground(TEXT);
            setFont(font(Font.BOLD, 13));
            setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
            addMouseListener(new MouseAdapter() {
                public void mouseEntered(MouseEvent e) {
                    hover = true;
                    repaint();
                }

                public void mouseExited(MouseEvent e) {
                    hover = false;
                    repaint();
                }
            });
        }

        @Override
        public Dimension getPreferredSize() {
            Dimension d = super.getPreferredSize();
            return new Dimension(d.width + 26, 36);
        }

        @Override
        protected void paintComponent(Graphics gr) {
            Graphics2D g = aa(gr);
            g.setColor(active ? ACCENT : hover ? CARD2 : CARD);
            g.fillRoundRect(0, 0, getWidth(), getHeight(), 14, 14);
            g.dispose();
            super.paintComponent(gr);
        }
    }

    static final class StatCard extends JPanel {
        final String title, value;
        final String[] sub;
        final Color accent;

        StatCard(String title, String value, Color accent, String... sub) {
            this.title = title;
            this.value = value;
            this.accent = accent;
            this.sub = sub;
            setOpaque(false);
            setPreferredSize(new Dimension(250, 108));
        }

        @Override
        protected void paintComponent(Graphics gr) {
            Graphics2D g = aa(gr);
            g.setColor(CARD);
            g.fillRoundRect(0, 0, getWidth(), getHeight(), 18, 18);
            g.setColor(accent);
            g.fillRoundRect(0, 14, 5, getHeight() - 28, 5, 5);
            g.setFont(font(Font.BOLD, 11));
            g.setColor(MUTED);
            g.drawString(title, 20, 26);
            g.setFont(font(Font.BOLD, 26));
            g.setColor(accent);
            g.drawString(value, 20, 58);
            g.setFont(font(Font.PLAIN, 12));
            g.setColor(MUTED);
            for (int i = 0; i < sub.length; i++)
                g.drawString(sub[i], 20, 78 + i * 16);
            g.dispose();
        }
    }

    static JLabel caption(String html) {
        return caption(html, 1000);
    }

    static JLabel caption(String html, int width) {
        JLabel l = new JLabel("<html><div style='width:" + width + "px'>" + html + "</div></html>");
        l.setPreferredSize(new Dimension(width, 42));
        l.setVerticalAlignment(SwingConstants.TOP);
        l.setForeground(MUTED);
        l.setFont(font(Font.PLAIN, 13));
        l.setBorder(new EmptyBorder(0, 2, 6, 0));
        return l;
    }

    static JPanel page(JComponent north, JComponent center) {
        JPanel p = new JPanel(new BorderLayout(0, 8));
        p.setBackground(BG);
        p.setBorder(new EmptyBorder(10, 18, 16, 18));
        if (north != null)
            p.add(north, BorderLayout.NORTH);
        p.add(center, BorderLayout.CENTER);
        return p;
    }

    // ---------- dark table ----------
    static final class DarkCell extends DefaultTableCellRenderer {
        final Set<Integer> right;

        DarkCell(Integer... r) {
            right = new HashSet<>(Arrays.asList(r));
        }

        @Override
        public Component getTableCellRendererComponent(JTable t, Object v, boolean sel,
                boolean foc, int row, int col) {
            super.getTableCellRendererComponent(t, v, sel, foc, row, col);
            String s = String.valueOf(v);
            setBackground(sel ? al(DC, 60) : row % 2 == 0 ? PANEL : new Color(0x0f1829));
            setForeground(s.equals("PASS") ? OK : s.equals("FAIL") ? BRUTE : TEXT);
            setFont(font(s.equals("PASS") || s.equals("FAIL") ? Font.BOLD : Font.PLAIN, 13));
            setHorizontalAlignment(right.contains(col) ? SwingConstants.RIGHT : SwingConstants.LEFT);
            setBorder(new EmptyBorder(0, 12, 0, 12));
            return this;
        }
    }

    static JScrollPane darkTable(DefaultTableModel m, Integer... rightCols) {
        JTable t = new JTable(m);
        t.setRowHeight(32);
        t.setBackground(PANEL);
        t.setGridColor(GRID);
        t.setShowVerticalLines(false);
        t.setDefaultRenderer(Object.class, new DarkCell(rightCols));
        JTableHeader h = t.getTableHeader();
        h.setReorderingAllowed(false);
        h.setPreferredSize(new Dimension(10, 34));
        h.setDefaultRenderer((tb, v, s, f, r, c) -> {
            JLabel l = new JLabel(String.valueOf(v));
            l.setOpaque(true);
            l.setBackground(CARD);
            l.setForeground(MUTED);
            l.setFont(font(Font.BOLD, 12));
            l.setBorder(new EmptyBorder(0, 12, 0, 12));
            l.setHorizontalAlignment(Arrays.asList(rightCols).contains(c) ? SwingConstants.RIGHT : SwingConstants.LEFT);
            return l;
        });
        JScrollPane sp = new JScrollPane(t);
        sp.getViewport().setBackground(PANEL);
        sp.setBorder(new LineBorder(GRID));
        return sp;
    }

    static DefaultTableModel model(String... cols) {
        return new DefaultTableModel(cols, 0) {
            @Override
            public boolean isCellEditable(int r, int c) {
                return false;
            }
        };
    }

    // =====================================================================
    // PLOT BASE (zoom with wheel, drag to pan, double click to reset, hover)
    // =====================================================================
    static final class Leg {
        final String name;
        final Color c;
        final int kind; // 0 dot, 1 line, 2 dashed line, 3 region

        Leg(String name, Color c, int kind) {
            this.name = name;
            this.c = c;
            this.kind = kind;
        }
    }

    static class Plot extends JPanel {
        final P[] pts;
        double bx0, bx1, by0, by1, vx0, vx1, vy0, vy1;
        final int ML = 62, MR = 20, MT = 16, MB = 46;
        final int rad;
        P hover;
        private Point dragFrom;
        private double dx0, dx1, dy0, dy1;

        Plot(P[] pts) {
            this.pts = pts;
            int n = pts.length;
            rad = n <= 150 ? 5 : n <= 600 ? 4 : n <= 3000 ? 3 : n <= 20000 ? 2 : 1;
            setBackground(PANEL);
            double minx = Double.MAX_VALUE, maxx = -Double.MAX_VALUE, miny = minx, maxy = maxx;
            for (P p : pts) {
                minx = Math.min(minx, p.x);
                maxx = Math.max(maxx, p.x);
                miny = Math.min(miny, p.y);
                maxy = Math.max(maxy, p.y);
            }
            double px = Math.max((maxx - minx) * 0.04, 1), py = Math.max((maxy - miny) * 0.04, 1);
            bx0 = minx - px;
            bx1 = maxx + px;
            by0 = miny - py;
            by1 = maxy + py;
            resetView();

            addMouseWheelListener(e -> {
                double f = Math.pow(1.18, e.getPreciseWheelRotation());
                double cx = wx(e.getX()), cy = wy(e.getY());
                double nx0 = cx - (cx - vx0) * f, nx1 = cx + (vx1 - cx) * f;
                double ny0 = cy - (cy - vy0) * f, ny1 = cy + (vy1 - cy) * f;
                if (nx1 - nx0 > 1e-4 && ny1 - ny0 > 1e-4) {
                    vx0 = nx0;
                    vx1 = nx1;
                    vy0 = ny0;
                    vy1 = ny1;
                }
                repaint();
            });
            MouseAdapter ma = new MouseAdapter() {
                public void mousePressed(MouseEvent e) {
                    dragFrom = e.getPoint();
                    dx0 = vx0;
                    dx1 = vx1;
                    dy0 = vy0;
                    dy1 = vy1;
                }

                public void mouseClicked(MouseEvent e) {
                    if (e.getClickCount() == 2)
                        resetView();
                }

                public void mouseDragged(MouseEvent e) {
                    if (dragFrom == null)
                        return;
                    double sxw = (dx1 - dx0) / pw(), syw = (dy1 - dy0) / ph();
                    double mx = (e.getX() - dragFrom.x) * sxw, my = (e.getY() - dragFrom.y) * syw;
                    vx0 = dx0 - mx;
                    vx1 = dx1 - mx;
                    vy0 = dy0 + my;
                    vy1 = dy1 + my;
                    repaint();
                }

                public void mouseMoved(MouseEvent e) {
                    if (pts.length > 200000)
                        return;
                    P best = null;
                    double bd = 12 * 12;
                    for (P p : pts) {
                        double ddx = sx(p.x) - e.getX(), ddy = sy(p.y) - e.getY();
                        double d = ddx * ddx + ddy * ddy;
                        if (d < bd) {
                            bd = d;
                            best = p;
                        }
                    }
                    if (best != hover) {
                        hover = best;
                        repaint();
                    }
                }
            };
            addMouseListener(ma);
            addMouseMotionListener(ma);
            setCursor(Cursor.getPredefinedCursor(Cursor.CROSSHAIR_CURSOR));
        }

        void resetView() {
            vx0 = bx0;
            vx1 = bx1;
            vy0 = by0;
            vy1 = by1;
            repaint();
        }

        int pw() {
            return Math.max(1, getWidth() - ML - MR);
        }

        int ph() {
            return Math.max(1, getHeight() - MT - MB);
        }

        Rectangle plotRect() {
            return new Rectangle(ML, MT, pw(), ph());
        }

        int sx(double x) {
            return ML + (int) Math.round((x - vx0) / (vx1 - vx0) * pw());
        }

        int sy(double y) {
            return MT + (int) Math.round((vy1 - y) / (vy1 - vy0) * ph());
        }

        double wx(int px) {
            return vx0 + (px - ML) * (vx1 - vx0) / pw();
        }

        double wy(int py) {
            return vy1 - (py - MT) * (vy1 - vy0) / ph();
        }

        // hooks for subclasses
        void underlay(Graphics2D g) {
        }

        void overlay(Graphics2D g) {
        }

        Color pointColor(P p) {
            return POINT;
        }

        Leg[] legend() {
            return null;
        }

        @Override
        protected void paintComponent(Graphics gr) {
            Graphics2D g = aa(gr);
            g.setColor(PANEL);
            g.fillRect(0, 0, getWidth(), getHeight());
            Rectangle pr = plotRect();
            g.setColor(PLOTBG);
            g.fillRect(pr.x, pr.y, pr.width, pr.height);

            double stx = niceStep((vx1 - vx0) / 9), sty = niceStep((vy1 - vy0) / 6);
            Shape old = g.getClip();
            g.setClip(pr);
            g.setStroke(new BasicStroke(1f));
            g.setColor(GRID);
            for (long k = (long) Math.ceil(vx0 / stx); k * stx <= vx1; k++) {
                int x = sx(k * stx);
                g.drawLine(x, pr.y, x, pr.y + pr.height);
            }
            for (long k = (long) Math.ceil(vy0 / sty); k * sty <= vy1; k++) {
                int y = sy(k * sty);
                g.drawLine(pr.x, y, pr.x + pr.width, y);
            }
            underlay(g);
            drawPoints(g);
            overlay(g);
            if (hover != null) {
                g.setColor(Color.WHITE);
                g.setStroke(new BasicStroke(1.5f));
                int r = rad + 5;
                g.drawOval(sx(hover.x) - r, sy(hover.y) - r, 2 * r, 2 * r);
            }
            drawLegend(g);
            g.setClip(old);

            g.setFont(font(Font.PLAIN, 11));
            FontMetrics fm = g.getFontMetrics();
            g.setColor(MUTED);
            for (long k = (long) Math.ceil(vx0 / stx); k * stx <= vx1; k++) {
                String s = tick(k * stx, stx);
                g.drawString(s, sx(k * stx) - fm.stringWidth(s) / 2, pr.y + pr.height + 16);
            }
            for (long k = (long) Math.ceil(vy0 / sty); k * sty <= vy1; k++) {
                String s = tick(k * sty, sty);
                g.drawString(s, pr.x - 8 - fm.stringWidth(s), sy(k * sty) + 4);
            }
            g.setColor(AXIS);
            g.drawRect(pr.x, pr.y, pr.width, pr.height);
            g.setColor(MUTED);
            g.setFont(font(Font.BOLD, 12));
            g.drawString("X", pr.x + pr.width / 2, getHeight() - 8);
            Graphics2D rot = (Graphics2D) g.create();
            rot.rotate(-Math.PI / 2, 16, pr.y + pr.height / 2);
            rot.drawString("Y", 16, pr.y + pr.height / 2);
            rot.dispose();
            g.setFont(font(Font.PLAIN, 11));
            String hint = "scroll: zoom   |   drag: pan   |   double-click: reset";
            g.setColor(al(MUTED, 170));
            g.drawString(hint, pr.x + pr.width - g.getFontMetrics().stringWidth(hint), getHeight() - 8);

            if (hover != null)
                pill(g, pt(hover), sx(hover.x) + 12, sy(hover.y) - 34, Color.WHITE, pr);
            g.dispose();
        }

        void drawPoints(Graphics2D g) {
            Rectangle pr = plotRect();
            for (P p : pts) {
                int x = sx(p.x), y = sy(p.y);
                if (x < pr.x - 6 || x > pr.x + pr.width + 6 || y < pr.y - 6 || y > pr.y + pr.height + 6)
                    continue;
                g.setColor(pointColor(p));
                if (rad <= 1)
                    g.fillRect(x - 1, y - 1, 2, 2);
                else
                    g.fillOval(x - rad, y - rad, 2 * rad, 2 * rad);
            }
        }

        void drawLegend(Graphics2D g) {
            Leg[] items = legend();
            if (items == null)
                return;
            g.setFont(font(Font.PLAIN, 12));
            FontMetrics fm = g.getFontMetrics();
            int w = 0;
            for (Leg l : items)
                w = Math.max(w, fm.stringWidth(l.name));
            w += 50;
            int h = items.length * 21 + 12, x = ML + 12, y = MT + 12;
            g.setColor(al(CARD, 228));
            g.fillRoundRect(x, y, w, h, 14, 14);
            g.setColor(GRID);
            g.setStroke(new BasicStroke(1f));
            g.drawRoundRect(x, y, w, h, 14, 14);
            for (int i = 0; i < items.length; i++) {
                Leg l = items[i];
                int cy = y + 18 + i * 21;
                g.setColor(l.c);
                switch (l.kind) {
                    case 0:
                        g.fillOval(x + 14, cy - 4, 9, 9);
                        break;
                    case 1:
                        g.setStroke(new BasicStroke(3f));
                        g.drawLine(x + 10, cy, x + 28, cy);
                        break;
                    case 2:
                        g.setStroke(DASH);
                        g.drawLine(x + 10, cy, x + 28, cy);
                        break;
                    default:
                        g.setColor(al(l.c, 90));
                        g.fillRect(x + 10, cy - 6, 18, 12);
                        g.setColor(l.c);
                        g.setStroke(new BasicStroke(1f));
                        g.drawRect(x + 10, cy - 6, 18, 12);
                }
                g.setColor(TEXT);
                g.drawString(l.name, x + 38, cy + 4);
            }
        }

        void drawPair(Graphics2D g, Result r, Color c, String name, int labelDy, int ring, float width) {
            if (r == null)
                return;
            int x1 = sx(r.a.x), y1 = sy(r.a.y), x2 = sx(r.b.x), y2 = sy(r.b.y);
            g.setStroke(new BasicStroke(width + 7, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
            g.setColor(al(c, 55));
            g.drawLine(x1, y1, x2, y2);
            g.setStroke(new BasicStroke(width, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
            g.setColor(c);
            g.drawLine(x1, y1, x2, y2);
            for (int[] q : new int[][] { { x1, y1 }, { x2, y2 } }) {
                g.setColor(al(c, 70));
                g.fillOval(q[0] - ring - 4, q[1] - ring - 4, 2 * ring + 8, 2 * ring + 8);
                g.setColor(c);
                g.fillOval(q[0] - ring + 2, q[1] - ring + 2, 2 * ring - 4, 2 * ring - 4);
                g.setColor(Color.WHITE);
                g.setStroke(new BasicStroke(1.5f));
                g.drawOval(q[0] - ring + 2, q[1] - ring + 2, 2 * ring - 4, 2 * ring - 4);
            }
            String label = (name.isEmpty() ? "" : name + "   ") + String.format(Locale.US, "d = %.6f", r.dist());
            pill(g, label, (x1 + x2) / 2 + 14, (y1 + y2) / 2 + labelDy, c, plotRect());
        }

        void splitLine(Graphics2D g, double x, Color c) {
            Rectangle pr = plotRect();
            g.setColor(c);
            g.setStroke(DASH);
            int px = sx(x);
            g.drawLine(px, pr.y, px, pr.y + pr.height);
        }

        void strip(Graphics2D g, double midX, double d) {
            Rectangle pr = plotRect();
            int xa = sx(midX - d), xb = sx(midX + d);
            g.setColor(al(STRIPC, 38));
            g.fillRect(xa, pr.y, Math.max(1, xb - xa), pr.height);
            g.setColor(al(STRIPC, 160));
            g.setStroke(new BasicStroke(1.2f));
            g.drawLine(xa, pr.y, xa, pr.y + pr.height);
            g.drawLine(xb, pr.y, xb, pr.y + pr.height);
            pill(g, String.format(Locale.US, "strip width 2d = %.3f", 2 * d),
                    (xa + xb) / 2 - 70, pr.y + pr.height - 34, STRIPC, pr);
        }
    }

    // ---------- concrete plots ----------
    static final class OverviewPlot extends Plot {
        final Result brute, dc;

        OverviewPlot(P[] pts, Result brute, Result dc) {
            super(pts);
            this.brute = brute;
            this.dc = dc;
        }

        @Override
        void overlay(Graphics2D g) {
            boolean same = brute.a == dc.a && brute.b == dc.b;
            if (same) {
                drawPair(g, brute, BRUTE, "", -30, 9, 3f);
                drawPair(g, dc, DC, "Both algorithms", -30, 6, 2f);
            } else {
                drawPair(g, brute, BRUTE, "Brute-Force", -30, 9, 3f);
                drawPair(g, dc, DC, "Divide & Conquer", 24, 6, 2f);
            }
        }

        @Override
        Leg[] legend() {
            return new Leg[] { new Leg("Input points", POINT, 0), new Leg("Brute-Force closest pair", BRUTE, 1),
                    new Leg("Divide & Conquer closest pair", DC, 1) };
        }
    }

    static final class BrutePlot extends Plot {
        final Result brute;

        BrutePlot(P[] pts, Result brute) {
            super(pts);
            this.brute = brute;
        }

        @Override
        void overlay(Graphics2D g) {
            drawPair(g, brute, BRUTE, "Brute-Force", -30, 8, 3f);
        }

        @Override
        Leg[] legend() {
            return new Leg[] { new Leg("Input points", POINT, 0), new Leg("Closest pair (Brute-Force)", BRUTE, 1) };
        }
    }

    static final class DCPlot extends Plot {
        final Result dc;
        final Step root;

        DCPlot(P[] pts, Result dc, Step root) {
            super(pts);
            this.dc = dc;
            this.root = root;
        }

        @Override
        Color pointColor(P p) {
            if (root != null && Math.abs(p.x - root.midX) < root.d)
                return STRIPC;
            return POINT;
        }

        @Override
        void underlay(Graphics2D g) {
            if (root == null)
                return;
            strip(g, root.midX, root.d);
            splitLine(g, root.midX, SPLITC);
        }

        @Override
        void overlay(Graphics2D g) {
            drawPair(g, dc, DC, "Divide & Conquer", -30, 8, 3f);
        }

        @Override
        Leg[] legend() {
            if (root == null)
                return new Leg[] { new Leg("Input points", POINT, 0), new Leg("Closest pair (D&C)", DC, 1) };
            return new Leg[] { new Leg("Input points", POINT, 0), new Leg("Points inside the strip", STRIPC, 0),
                    new Leg("Dividing line (median x)", SPLITC, 2), new Leg("Strip region (width 2d)", STRIPC, 3),
                    new Leg("Closest pair (D&C)", DC, 1) };
        }
    }

    static final class AnimPlot extends Plot {
        final Anim anim;
        Step step;

        AnimPlot(P[] pts, Anim anim) {
            super(pts);
            this.anim = anim;
        }

        void setStep(Step s) {
            step = s;
            repaint();
        }

        @Override
        Color pointColor(P p) {
            if (step == null)
                return POINT;
            int r = p.rank;
            if (step.kind == DONE)
                return TEXT;
            if (r < step.lo || r >= step.hi)
                return DIM;
            if (step.kind == BASE)
                return AMBER;
            if (step.kind == MERGE && step.strip.contains(p))
                return STRIPC;
            return r < step.mid ? TEAL : PURPLE;
        }

        @Override
        void underlay(Graphics2D g) {
            if (step == null)
                return;
            Rectangle pr = plotRect();
            if (step.kind != DONE) {
                int x0 = sx(anim.px[step.lo].x), x1 = sx(anim.px[step.hi - 1].x);
                g.setColor(new Color(255, 255, 255, 14));
                g.fillRect(x0, pr.y, Math.max(2, x1 - x0), pr.height);
                g.setColor(al(TEXT, 70));
                g.setStroke(new BasicStroke(1f));
                g.drawLine(x0, pr.y, x0, pr.y + pr.height);
                g.drawLine(x1, pr.y, x1, pr.y + pr.height);
            }
            for (double a : step.anc)
                splitLine(g, a, al(SPLITC, 60));
            if (step.kind == MERGE)
                strip(g, step.midX, step.d);
            if (step.mid >= 0)
                splitLine(g, step.midX, SPLITC);
        }

        @Override
        void overlay(Graphics2D g) {
            if (step != null && step.pair != null)
                drawPair(g, step.pair, step.kind == BASE ? AMBER : DC, "", -30, 7, 3f);
        }

        @Override
        Leg[] legend() {
            return new Leg[] { new Leg("Left half", TEAL, 0), new Leg("Right half", PURPLE, 0),
                    new Leg("Strip candidates", STRIPC, 0), new Leg("Base-case points", AMBER, 0),
                    new Leg("Split line", SPLITC, 2),
                    new Leg("Best pair so far", DC, 1) };
        }
    }

    // =====================================================================
    // ANIMATION PAGE
    // =====================================================================
    static final class AnimPage extends JPanel {
        final Anim anim;
        final AnimPlot plot;
        final JLabel cap = new JLabel();
        final JSlider slider;
        final FlatButton play = new FlatButton("Play");
        final javax.swing.Timer timer;
        int idx = 0;
        boolean started, adjusting;
        double speed = 1;

        AnimPage(P[] pts, Anim anim) {
            super(new BorderLayout(0, 8));
            this.anim = anim;
            setBackground(BG);
            setBorder(new EmptyBorder(10, 18, 16, 18));
            plot = new AnimPlot(pts, anim);
            cap.setForeground(TEXT);
            cap.setFont(font(Font.PLAIN, 14));
            cap.setPreferredSize(new Dimension(100, 48));
            add(cap, BorderLayout.NORTH);
            add(plot, BorderLayout.CENTER);

            FlatButton restart = new FlatButton("Restart"), prev = new FlatButton("Prev"),
                    next = new FlatButton("Next");
            timer = new javax.swing.Timer(1100, e -> {
                if (idx < last())
                    setIdx(idx + 1);
                else
                    stop();
            });
            slider = new JSlider(0, anim.steps.size() - 1, 0);
            slider.setBackground(BG);
            slider.addChangeListener(e -> {
                if (!adjusting) {
                    stop();
                    setIdx(slider.getValue());
                }
            });
            JComboBox<String> sp = new JComboBox<>(new String[] { "0.5x", "1x", "2x", "4x" });
            sp.setSelectedIndex(1);
            sp.setBackground(CARD);
            sp.setForeground(TEXT);
            sp.addActionListener(e -> {
                speed = Double.parseDouble(((String) sp.getSelectedItem()).replace("x", ""));
                timer.setDelay((int) (1100 / speed));
            });
            JPanel left = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 0));
            left.setBackground(BG);
            left.add(restart);
            left.add(prev);
            left.add(play);
            left.add(next);
            JPanel right = new JPanel(new FlowLayout(FlowLayout.RIGHT, 8, 0));
            right.setBackground(BG);
            JLabel sl = new JLabel("Speed");
            sl.setForeground(MUTED);
            right.add(sl);
            right.add(sp);
            JPanel bar = new JPanel(new BorderLayout(12, 0));
            bar.setBackground(BG);
            bar.add(left, BorderLayout.WEST);
            bar.add(slider, BorderLayout.CENTER);
            bar.add(right, BorderLayout.EAST);
            add(bar, BorderLayout.SOUTH);

            restart.addActionListener(e -> {
                stop();
                setIdx(0);
            });
            prev.addActionListener(e -> {
                stop();
                setIdx(Math.max(0, idx - 1));
            });
            next.addActionListener(e -> {
                stop();
                setIdx(Math.min(last(), idx + 1));
            });
            play.addActionListener(e -> {
                if (timer.isRunning())
                    stop();
                else
                    play();
            });
            addComponentListener(new ComponentAdapter() {
                public void componentShown(ComponentEvent e) {
                    if (!started) {
                        started = true;
                        play();
                    }
                }

                public void componentHidden(ComponentEvent e) {
                    stop();
                }
            });
            setIdx(0);
        }

        int last() {
            return anim.steps.size() - 1;
        }

        void play() {
            if (idx >= last())
                setIdx(0);
            timer.start();
            play.setText("Pause");
        }

        void stop() {
            timer.stop();
            play.setText("Play");
        }

        void setIdx(int i) {
            idx = i;
            Step s = anim.steps.get(i);
            plot.setStep(s);
            adjusting = true;
            slider.setValue(i);
            adjusting = false;
            cap.setText("<html><b style='color:#38bdf8'>Step " + (i + 1) + " / " + anim.steps.size() + " - "
                    + s.title + "</b><br>" + s.text + "</html>");
            if (i >= last())
                stop();
        }
    }

    // =====================================================================
    // PERFORMANCE PAGE
    // =====================================================================
    static final class PerfChart extends JPanel {
        final List<Bench> data;
        boolean log;
        int hov = -1;
        final int ML = 84, MR = 30, MT = 24, MB = 56;

        PerfChart(List<Bench> data) {
            this.data = data;
            setBackground(PANEL);
            addMouseMotionListener(new MouseAdapter() {
                public void mouseMoved(MouseEvent e) {
                    int best = -1;
                    double bd = 1e18;
                    for (int i = 0; i < data.size(); i++) {
                        double d = Math.abs(xOf(i) - e.getX());
                        if (d < bd) {
                            bd = d;
                            best = i;
                        }
                    }
                    if (best != hov) {
                        hov = best;
                        repaint();
                    }
                }
            });
        }

        double xOf(int i) {
            return ML + (i + 0.5) / data.size() * (getWidth() - ML - MR);
        }

        @Override
        protected void paintComponent(Graphics gr) {
            Graphics2D g = aa(gr);
            g.setColor(PANEL);
            g.fillRect(0, 0, getWidth(), getHeight());
            int pw = getWidth() - ML - MR, ph = getHeight() - MT - MB;
            if (pw < 10 || ph < 10 || data.isEmpty()) {
                g.dispose();
                return;
            }

            double maxT = 1e-9, minPos = Double.MAX_VALUE;
            for (Bench b : data)
                for (double t : new double[] { b.bruteMs, b.dcMs }) {
                    maxT = Math.max(maxT, t);
                    if (t > 0)
                        minPos = Math.min(minPos, t);
                }
            if (minPos == Double.MAX_VALUE)
                minPos = 1e-3;
            double ymin, ymax;
            if (log) {
                ymin = Math.pow(10, Math.floor(Math.log10(minPos)));
                ymax = Math.pow(10, Math.ceil(Math.log10(maxT)));
                if (ymax <= ymin)
                    ymax = ymin * 10;
            } else {
                double step = niceStep(maxT / 5);
                ymin = 0;
                ymax = Math.ceil(maxT / step) * step;
            }
            final double fmin = ymin, fmax = ymax;
            java.util.function.DoubleUnaryOperator yOf = t -> {
                double f = log
                        ? (Math.log10(Math.max(t, fmin)) - Math.log10(fmin)) / (Math.log10(fmax) - Math.log10(fmin))
                        : t / fmax;
                return MT + ph - f * ph;
            };

            g.setColor(PLOTBG);
            g.fillRect(ML, MT, pw, ph);
            g.setFont(font(Font.PLAIN, 11));
            FontMetrics fm = g.getFontMetrics();
            g.setStroke(new BasicStroke(1f));
            if (log) {
                for (double v = ymin; v <= ymax * 1.0001; v *= 10) {
                    int y = (int) yOf.applyAsDouble(v);
                    g.setColor(GRID);
                    g.drawLine(ML, y, ML + pw, y);
                    String s = v >= 1 ? String.valueOf((long) v)
                            : String.format(Locale.US, "%." + (int) Math.round(-Math.log10(v)) + "f", v);
                    g.setColor(MUTED);
                    g.drawString(s, ML - 10 - fm.stringWidth(s), y + 4);
                }
            } else {
                double step = niceStep(maxT / 5);
                for (double v = 0; v <= ymax + step / 2; v += step) {
                    int y = (int) yOf.applyAsDouble(v);
                    g.setColor(GRID);
                    g.drawLine(ML, y, ML + pw, y);
                    String s = tick(v, Math.min(step, 1));
                    g.setColor(MUTED);
                    g.drawString(s, ML - 10 - fm.stringWidth(s), y + 4);
                }
            }
            for (int i = 0; i < data.size(); i++) {
                int x = (int) xOf(i);
                g.setColor(GRID);
                g.drawLine(x, MT, x, MT + ph);
                String s = String.valueOf(data.get(i).n);
                g.setColor(MUTED);
                g.drawString(s, x - fm.stringWidth(s) / 2, MT + ph + 18);
            }
            g.setColor(AXIS);
            g.drawRect(ML, MT, pw, ph);
            g.setColor(MUTED);
            g.setFont(font(Font.BOLD, 12));
            g.drawString("Number of points N", ML + pw / 2 - 55, getHeight() - 12);
            Graphics2D rot = (Graphics2D) g.create();
            rot.rotate(-Math.PI / 2, 18, MT + ph / 2 + 40);
            rot.drawString(log ? "Time (ms, log scale)" : "Time (ms)", 18, MT + ph / 2 + 40);
            rot.dispose();

            for (int s = 0; s < 2; s++) {
                Color c = s == 0 ? BRUTE : DC;
                int n = data.size();
                int[] xs = new int[n + 2], ys = new int[n + 2];
                for (int i = 0; i < n; i++) {
                    xs[i] = (int) xOf(i);
                    ys[i] = (int) yOf.applyAsDouble(s == 0 ? data.get(i).bruteMs : data.get(i).dcMs);
                }
                xs[n] = xs[n - 1];
                ys[n] = MT + ph;
                xs[n + 1] = xs[0];
                ys[n + 1] = MT + ph;
                g.setColor(al(c, 28));
                g.fillPolygon(xs, ys, n + 2);
                g.setColor(c);
                g.setStroke(new BasicStroke(3f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
                for (int i = 1; i < n; i++)
                    g.drawLine(xs[i - 1], ys[i - 1], xs[i], ys[i]);
                for (int i = 0; i < n; i++) {
                    g.setColor(PANEL);
                    g.fillOval(xs[i] - 6, ys[i] - 6, 12, 12);
                    g.setColor(c);
                    g.fillOval(xs[i] - 4, ys[i] - 4, 8, 8);
                }
            }

            // legend
            g.setFont(font(Font.PLAIN, 12));
            String[] names = { "Brute-Force  O(N^2)", "Divide & Conquer  O(N log N)" };
            g.setColor(al(CARD, 230));
            g.fillRoundRect(ML + 14, MT + 12, 232, 56, 14, 14);
            for (int i = 0; i < 2; i++) {
                g.setColor(i == 0 ? BRUTE : DC);
                g.setStroke(new BasicStroke(3f));
                g.drawLine(ML + 26, MT + 32 + i * 22, ML + 46, MT + 32 + i * 22);
                g.setColor(TEXT);
                g.drawString(names[i], ML + 56, MT + 36 + i * 22);
            }

            if (hov >= 0) {
                Bench b = data.get(hov);
                int x = (int) xOf(hov);
                g.setColor(al(TEXT, 90));
                g.setStroke(DASH);
                g.drawLine(x, MT, x, MT + ph);
                String[] rows = { "N = " + b.n,
                        String.format(Locale.US, "Brute-Force  %.3f ms", b.bruteMs),
                        String.format(Locale.US, "Divide & Conquer  %.3f ms", b.dcMs),
                        String.format(Locale.US, "Speed-up  %.1fx", b.bruteMs / Math.max(b.dcMs, 1e-9)) };
                g.setFont(font(Font.BOLD, 12));
                int w = 0;
                for (String r : rows)
                    w = Math.max(w, g.getFontMetrics().stringWidth(r));
                int bx = Math.min(x + 14, ML + pw - w - 30), by = MT + ph / 2 - 40;
                g.setColor(al(CARD, 245));
                g.fillRoundRect(bx, by, w + 24, 88, 12, 12);
                g.setColor(GRID);
                g.setStroke(new BasicStroke(1f));
                g.drawRoundRect(bx, by, w + 24, 88, 12, 12);
                Color[] cols = { TEXT, BRUTE, DC, OK };
                for (int i = 0; i < 4; i++) {
                    g.setColor(cols[i]);
                    g.drawString(rows[i], bx + 12, by + 22 + i * 20);
                }
            }
            g.dispose();
        }
    }

    static JPanel perfPage(List<Bench> bench) {
        PerfChart chart = new PerfChart(bench);
        FlatButton logBtn = new FlatButton("Log scale: off");
        logBtn.addActionListener(e -> {
            chart.log = !chart.log;
            logBtn.setText("Log scale: " + (chart.log ? "on" : "off"));
            logBtn.active = chart.log;
            chart.repaint();
        });
        DefaultTableModel m = model("N", "Brute-Force (ms)", "D&C (ms)", "Speed-up");
        for (Bench b : bench)
            m.addRow(new Object[] { b.n, String.format(Locale.US, "%.3f", b.bruteMs),
                    String.format(Locale.US, "%.3f", b.dcMs),
                    String.format(Locale.US, "%.1fx", b.bruteMs / Math.max(b.dcMs, 1e-9)) });
        JScrollPane table = darkTable(m, 0, 1, 2, 3);
        table.setPreferredSize(new Dimension(380, 100));

        JPanel top = new JPanel(new BorderLayout());
        top.setBackground(BG);
        top.add(caption("Best-of-several timings on random inputs. Brute-Force grows quadratically, Divide &amp; "
                + "Conquer grows like N log N, so the gap widens as N increases. Hover the chart for details.", 700),
                BorderLayout.CENTER);
        JPanel btn = new JPanel(new FlowLayout(FlowLayout.RIGHT, 0, 0));
        btn.setBackground(BG);
        btn.add(logBtn);
        top.add(btn, BorderLayout.EAST);
        JPanel body = new JPanel(new BorderLayout(14, 0));
        body.setBackground(BG);
        body.add(chart, BorderLayout.CENTER);
        body.add(table, BorderLayout.EAST);
        return page(top, body);
    }

    // =====================================================================
    // VERIFICATION
    // =====================================================================
    interface Gen {
        P[] make(Random r);
    }

    static final class Scenario {
        final String name, desc;
        final int trials;
        final Gen gen;

        Scenario(String name, String desc, int trials, Gen gen) {
            this.name = name;
            this.desc = desc;
            this.trials = trials;
            this.gen = gen;
        }
    }

    static boolean agree(P[] pts) {
        Result b = bruteForce(pts), d = divideConquer(pts);
        if (pts.length < 2)
            return b == null && d == null;
        if (b == null || d == null)
            return false;
        if (Math.abs(b.dist() - d.dist()) > 1e-9 * (1 + b.dist()))
            return false;
        return valid(b) && valid(d);
    }

    static boolean valid(Result r) {
        return r.a != r.b && Math.abs(Math.sqrt(d2(r.a, r.b)) - r.dist()) <= 1e-12 * (1 + r.dist());
    }

    static P[] gen(Random r, int n, java.util.function.IntFunction<P> f) {
        P[] p = new P[n];
        for (int i = 0; i < n; i++)
            p[i] = f.apply(i);
        return p;
    }

    static List<Scenario> scenarios() {
        List<Scenario> s = new ArrayList<>();
        s.add(new Scenario("N < 2", "N = 0 or 1: no pair exists, both return nothing", 50,
                r -> gen(r, r.nextInt(2), i -> new P(r.nextInt(100), r.nextInt(100)))));
        s.add(new Scenario("N = 2", "the only possible pair", 300,
                r -> gen(r, 2, i -> new P(r.nextInt(1000), r.nextInt(1000)))));
        s.add(new Scenario("N = 3", "base case of the recursion", 300,
                r -> gen(r, 3, i -> new P(r.nextInt(1000), r.nextInt(1000)))));
        s.add(new Scenario("All points identical", "every distance is 0", 200, r -> {
            int x = r.nextInt(50), y = r.nextInt(50);
            return gen(r, 2 + r.nextInt(50), i -> new P(x, y));
        }));
        s.add(new Scenario("Duplicate points", "tiny coordinate range forces repeats", 400,
                r -> gen(r, 2 + r.nextInt(80), i -> new P(r.nextInt(5), r.nextInt(5)))));
        s.add(new Scenario("Collinear, same y", "all points on a horizontal line", 300, r -> {
            int y = r.nextInt(100);
            return gen(r, 2 + r.nextInt(200), i -> new P(r.nextInt(1000), y));
        }));
        s.add(new Scenario("Collinear, same x", "all points on a vertical line (all share the split x)", 300, r -> {
            int x = r.nextInt(100);
            return gen(r, 2 + r.nextInt(200), i -> new P(x, r.nextInt(1000)));
        }));
        s.add(new Scenario("Collinear, diagonal", "points on y = 2x + 1", 300,
                r -> gen(r, 2 + r.nextInt(200), i -> {
                    int x = r.nextInt(1000);
                    return new P(x, 2 * x + 1);
                })));
        s.add(new Scenario("Lattice grid", "many equal distances and shared x / y values", 300,
                r -> gen(r, 2 + r.nextInt(120), i -> new P(10 * r.nextInt(15), 10 * r.nextInt(15)))));
        s.add(new Scenario("Random integers", "uniform in [0, 1000]", 300,
                r -> gen(r, 2 + r.nextInt(400), i -> new P(r.nextInt(1001), r.nextInt(1001)))));
        s.add(new Scenario("Random floating point", "uniform doubles in [0, 1000)", 300,
                r -> gen(r, 2 + r.nextInt(400), i -> new P(r.nextDouble() * 1000, r.nextDouble() * 1000))));
        s.add(new Scenario("Large random", "N = 5000", 10,
                r -> gen(r, 5000, i -> new P(r.nextInt(50001), r.nextInt(50001)))));
        return s;
    }

    static final class VerifyPage extends JPanel {
        final DefaultTableModel model = model("Scenario", "What it checks", "Trials", "Passed", "Result");
        final JLabel summary = new JLabel("Running verification suite...");

        VerifyPage(boolean thisRunMatches, double thisDiff) {
            super(new BorderLayout(0, 8));
            setBackground(BG);
            setBorder(new EmptyBorder(10, 18, 16, 18));
            summary.setForeground(TEXT);
            summary.setFont(font(Font.BOLD, 15));
            JPanel top = new JPanel(new BorderLayout());
            top.setBackground(BG);
            top.add(caption("Randomised cross-check: for every trial both algorithms must report the same "
                    + "minimum distance, and the reported pair must really be that far apart."), BorderLayout.NORTH);
            top.add(summary, BorderLayout.SOUTH);
            add(top, BorderLayout.NORTH);
            JScrollPane table = darkTable(model, 2, 3);
            TableColumnModel cm = ((JTable) table.getViewport().getView()).getColumnModel();
            int[] w = { 200, 560, 90, 90, 90 };
            for (int i = 0; i < w.length; i++)
                cm.getColumn(i).setPreferredWidth(w[i]);
            add(table, BorderLayout.CENTER);

            new SwingWorker<Void, Object[]>() {
                int passAll = 0, totalAll = 0;

                @Override
                protected Void doInBackground() {
                    Random rng = new Random(2024);
                    for (Scenario sc : scenarios()) {
                        int ok = 0;
                        for (int t = 0; t < sc.trials; t++)
                            if (agree(sc.gen.make(rng)))
                                ok++;
                        passAll += ok;
                        totalAll += sc.trials;
                        publish(new Object[] { sc.name, sc.desc, sc.trials, ok, ok == sc.trials ? "PASS" : "FAIL" });
                    }
                    return null;
                }

                @Override
                protected void process(List<Object[]> rows) {
                    for (Object[] r : rows)
                        model.addRow(r);
                }

                @Override
                protected void done() {
                    boolean all = passAll == totalAll && thisRunMatches;
                    summary.setForeground(all ? OK : BRUTE);
                    summary.setText(String.format(Locale.US,
                            "%s   -   %d / %d random trials agree, and the current run matches (|difference| = %.1e)",
                            all ? "ALL TESTS PASSED" : "MISMATCH FOUND", passAll, totalAll, thisDiff));
                }
            }.execute();
        }
    }

    // =====================================================================
    // MAIN WINDOW
    // =====================================================================
    static JPanel buildUI(P[] pts, Result brute, Result dc, double bruteMs, double dcMs,
            List<Bench> bench, long seed) {
        Anim anim = new Anim(pts);
        double diff = Math.abs(brute.dist() - dc.dist());
        boolean match = diff <= 1e-9 * (1 + brute.dist());

        JPanel root = new JPanel(new BorderLayout());
        root.setBackground(BG);

        JLabel title = new JLabel("Closest Pair of Points");
        title.setFont(font(Font.BOLD, 28));
        title.setForeground(TEXT);
        JLabel sub = new JLabel(String.format(Locale.US,
                "Brute-Force vs Divide-and-Conquer   |   N = %d   |   coordinates in [0, %d]   |   seed %d",
                pts.length, rangeFor(pts.length), seed));
        sub.setFont(font(Font.PLAIN, 13));
        sub.setForeground(MUTED);
        JPanel titles = new JPanel(new GridLayout(2, 1));
        titles.setOpaque(false);
        titles.add(title);
        titles.add(sub);

        double speed = bruteMs / Math.max(dcMs, 1e-9);
        JPanel cards = new JPanel(new GridLayout(1, 4, 14, 0));
        cards.setOpaque(false);
        cards.add(new StatCard("BRUTE-FORCE", String.format(Locale.US, "%.6f", brute.dist()), BRUTE,
                pt(brute.a) + "  " + pt(brute.b), String.format(Locale.US, "time  %.3f ms", bruteMs)));
        cards.add(new StatCard("DIVIDE & CONQUER", String.format(Locale.US, "%.6f", dc.dist()), DC,
                pt(dc.a) + "  " + pt(dc.b), String.format(Locale.US, "time  %.3f ms", dcMs)));
        cards.add(new StatCard("SPEED-UP (BRUTE / D&C)", String.format(Locale.US, "%.1fx", speed), STRIPC,
                speed >= 1 ? "Divide & Conquer is faster" : "Brute-Force is faster at this small N",
                "see the Performance tab for larger N"));
        cards.add(new StatCard("AGREEMENT", match ? "MATCH" : "MISMATCH", match ? OK : BRUTE,
                "both give the same minimum distance",
                String.format(Locale.US, "|d1 - d2| = %.1e", diff)));

        JPanel header = new JPanel(new BorderLayout(0, 14));
        header.setBackground(BG);
        header.setBorder(new EmptyBorder(18, 18, 6, 18));
        header.add(titles, BorderLayout.NORTH);
        header.add(cards, BorderLayout.CENTER);

        // pages
        long pairs = (long) pts.length * (pts.length - 1) / 2;
        Step rootStep = anim.rootMerge;
        String dcText = rootStep == null
                ? "Fewer than 4 points: the recursion immediately hits its base case and uses brute force."
                : String.format(Locale.US,
                        "Sort by x, split at the median x = %s, solve both halves (d = min(left, right) = "
                                + "%.3f), then check only points with |x - %s| &lt; d, each against a few neighbours in y order.",
                        fmt(rootStep.midX), rootStep.d, fmt(rootStep.midX));

        String[] names = { "Overview", "Brute Force", "Divide & Conquer", "Animation", "Performance", "Verification" };
        JComponent[] pages = {
                page(caption(String.format(Locale.US, "Both closest pairs on the same plane. Red = Brute-Force, blue = "
                        + "Divide &amp; Conquer. When several pairs tie, the two algorithms may pick different pairs "
                        + "with the same distance (%.6f).", brute.dist())), new OverviewPlot(pts, brute, dc)),
                page(caption(
                        String.format(Locale.US, "Brute-Force checks every one of the N(N-1)/2 = %,d pairs - O(N^2).",
                                pairs)),
                        new BrutePlot(pts, brute)),
                page(caption(dcText), new DCPlot(pts, dc, rootStep)),
                new AnimPage(pts, anim),
                perfPage(bench),
                new VerifyPage(match, diff) };

        CardLayout cl = new CardLayout();
        JPanel content = new JPanel(cl);
        content.setBackground(BG);
        JPanel nav = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 6));
        nav.setBackground(BG);
        nav.setBorder(new EmptyBorder(0, 10, 0, 10));
        List<FlatButton> buttons = new ArrayList<>();
        for (int i = 0; i < names.length; i++) {
            content.add(pages[i], names[i]);
            FlatButton b = new FlatButton(names[i]);
            final String nm = names[i];
            b.addActionListener(e -> {
                cl.show(content, nm);
                for (FlatButton o : buttons) {
                    o.active = (o == b);
                    o.repaint();
                }
            });
            buttons.add(b);
            nav.add(b);
        }
        buttons.get(0).active = true;

        JPanel south = new JPanel(new BorderLayout());
        south.setBackground(BG);
        south.add(nav, BorderLayout.NORTH);
        south.add(content, BorderLayout.CENTER);
        root.add(header, BorderLayout.NORTH);
        root.add(south, BorderLayout.CENTER);
        root.putClientProperty("buttons", buttons);
        return root;
    }

    // =====================================================================
    // ENTRY POINT
    // =====================================================================
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        System.err.print("Enter number of points N: ");
        int n;
        try {
            n = sc.nextInt();
        } catch (NoSuchElementException ex) {
            System.out.println("Invalid input: N must be an integer.");
            return;
        }
        if (n < 2) {
            System.out.println("N must be at least 2: a closest pair needs two points.");
            return;
        }
        if (n > 200_000) {
            System.out.println("N is too large for the O(N^2) brute-force run (maximum 200000).");
            return;
        }
        long seed = args.length > 0 ? parseSeed(args[0]) : System.nanoTime() & 0xFFFFFFL;

        P[] pts = makePoints(n, seed, rangeFor(n));
        warmUp();
        int reps = n <= 20000 ? 3 : 1;
        Result[] res = new Result[2];
        double bruteMs = timeMs(() -> res[0] = bruteForce(pts), reps);
        double dcMs = timeMs(() -> res[1] = divideConquer(pts), reps);

        System.out.println(line(res[0]));
        System.out.println(line(res[1]));
        System.out.printf(Locale.US, "%.3f ms %.3f ms%n", bruteMs, dcMs);

        if (GraphicsEnvironment.isHeadless())
            return;
        List<Bench> bench = benchmark();
        SwingUtilities.invokeLater(() -> {
            try {
                UIManager.setLookAndFeel(UIManager.getCrossPlatformLookAndFeelClassName());
            } catch (Exception ignored) {
            }
            JFrame f = new JFrame("Closest Pair of Points - Brute-Force vs Divide-and-Conquer");
            f.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            f.setContentPane(buildUI(pts, res[0], res[1], bruteMs, dcMs, bench, seed));
            f.setSize(1240, 900);
            f.setMinimumSize(new Dimension(980, 700));
            f.setLocationRelativeTo(null);
            f.setVisible(true);
        });
    }

    static long parseSeed(String s) {
        try {
            return Long.parseLong(s.trim());
        } catch (NumberFormatException e) {
            return 42;
        }
    }
}