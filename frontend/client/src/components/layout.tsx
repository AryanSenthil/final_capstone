import { useState } from "react";
import { Link, useLocation } from "wouter";
import { useTheme } from "next-themes";
import { Database, FileText, Menu, X, PanelLeftClose, PanelLeftOpen, ChevronLeft, ChevronRight, Sun, Moon, Rocket, Layers, ScrollText } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

export default function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { theme, setTheme } = useTheme();

  const navItems = [
    { label: "Database", href: "/", icon: Database },
    { label: "Raw Files", href: "/raw", icon: FileText },
    { label: "Training", href: "/training", icon: Rocket },
    { label: "Models", href: "/models", icon: Layers },
    { label: "Reports", href: "/reports", icon: ScrollText },
  ];

  return (
    <div className="min-h-screen flex font-sans bg-background text-foreground">
      {/* Desktop Sidebar */}
      <aside
        className={cn(
          "hidden md:flex flex-col border-r border-border bg-sidebar text-sidebar-foreground transition-all duration-300 ease-in-out relative z-20",
          isCollapsed ? "w-16" : "w-56"
        )}
      >
        {/* Sidebar Header */}
        <div className="h-14 flex items-center px-4 border-b border-sidebar-border">
          {!isCollapsed && (
            <div className="flex items-center gap-2 font-bold text-lg tracking-tight text-primary overflow-hidden whitespace-nowrap">
               Aryan Senthil
            </div>
          )}
          {isCollapsed && (
             <div className="mx-auto">
               <Database className="h-5 w-5 text-primary" />
             </div>
          )}
        </div>

        {/* Navigation Links - "History Tab" style */}
        <div className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          {!isCollapsed && (
             <div className="px-2 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
               Navigation
             </div>
          )}

          {navItems.map((item) => (
            <Link key={item.href} href={item.href}>
              <a
                className={cn(
                  "flex items-center gap-2 px-2 py-2 rounded-md text-sm font-medium transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground group",
                  location === item.href || (item.href !== "/" && location.startsWith(item.href))
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-muted-foreground",
                  isCollapsed && "justify-center"
                )}
                title={isCollapsed ? item.label : undefined}
              >
                <item.icon className={cn("h-4 w-4 shrink-0", location === item.href && "text-primary")} />
                {!isCollapsed && <span className="truncate">{item.label}</span>}
              </a>
            </Link>
          ))}
        </div>

        {/* Sidebar Footer / Collapse Toggle */}
        <div className="p-2 border-t border-sidebar-border flex flex-col gap-1">
          <Button
            variant="ghost"
            size="sm"
            className={cn("w-full hover:bg-sidebar-accent hover:text-sidebar-accent-foreground", isCollapsed ? "px-0" : "justify-start")}
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            title="Toggle Theme"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {!isCollapsed && <span className="ml-2">Theme</span>}
          </Button>

          <Button
            variant="ghost"
            size="sm"
            className={cn("w-full hover:bg-sidebar-accent hover:text-sidebar-accent-foreground", isCollapsed ? "px-0" : "justify-start")}
            onClick={() => setIsCollapsed(!isCollapsed)}
          >
            {isCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4 mr-2" />}
            {!isCollapsed && "Collapse"}
          </Button>
        </div>
      </aside>

      {/* Mobile Header & Content Wrapper */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile Header */}
        <header className="md:hidden sticky top-0 z-50 w-full border-b border-border bg-background/80 backdrop-blur flex items-center px-4 h-14">
          <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="-ml-2">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0">
              <div className="h-14 flex items-center px-4 border-b border-border font-bold text-lg text-primary">
                Aryan Senthil
              </div>
              <div className="flex flex-col gap-1 p-2">
                 {navItems.map((item) => (
                    <Link key={item.href} href={item.href}>
                      <a
                        onClick={() => setIsMobileMenuOpen(false)}
                        className={cn(
                          "flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                          location === item.href
                            ? "bg-primary/10 text-primary"
                            : "hover:bg-muted"
                        )}
                      >
                        <item.icon className="h-4 w-4" />
                        {item.label}
                      </a>
                    </Link>
                  ))}
              </div>
            </SheetContent>
          </Sheet>
          <span className="font-bold text-lg ml-2 text-primary">Aryan Senthil</span>
        </header>

        {/* Main Content Area - Wider */}
        <main className="flex-1 p-4 sm:p-6 overflow-y-auto">
           <div className="max-w-[1600px] mx-auto w-full">
             {children}
           </div>
        </main>
      </div>
    </div>
  );
}
