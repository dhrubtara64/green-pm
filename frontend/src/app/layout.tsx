import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Green PM",
  description: "Engineering Project Intelligence — Evidence-backed progress and confidence for EPC projects",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <div className="flex h-screen overflow-hidden">
          <nav className="w-56 shrink-0 bg-white border-r border-slate-200 flex flex-col">
            <div className="px-4 py-5 border-b border-slate-200">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-md bg-gpm-green flex items-center justify-center">
                  <span className="text-white text-xs font-black">G</span>
                </div>
                <span className="text-slate-900 font-semibold text-sm">Green PM</span>
              </div>
              <p className="text-slate-500 text-xs mt-1.5">Northgate CCGT — Demo</p>
            </div>

            <div className="flex-1 px-2 py-4 space-y-1">
              <NavLink href="/" label="Dashboard" icon="▤" />
              <NavLink href="/reports" label="Weekly Report" icon="◧" />
            </div>

            <div className="px-4 py-3 border-t border-slate-200">
              <p className="text-slate-400 text-xs">Sourced from your schedule &amp; documents</p>
            </div>
          </nav>

          <main className="flex-1 overflow-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

function NavLink({ href, label, icon }: { href: string; label: string; icon: string }) {
  return (
    <a
      href={href}
      className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-slate-600
                 hover:text-slate-900 hover:bg-slate-100 transition-colors text-sm"
    >
      <span className="text-slate-400 text-base">{icon}</span>
      {label}
    </a>
  );
}
