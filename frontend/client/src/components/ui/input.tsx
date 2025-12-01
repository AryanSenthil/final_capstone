import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          // Base layout and typography
          "flex h-9 w-full rounded-md px-3 py-1 text-base md:text-sm",
          // Glass effect: subtle backdrop blur with semi-transparent background
          "glass-light bg-transparent backdrop-blur-sm",
          // Border: glass border with focus glow
          "border border-[--glass-border]",
          // Shadow: subtle depth
          "shadow-sm",
          // Transitions: smooth for all properties
          "transition-all duration-200",
          // Focus state: glass glow and enhanced border
          "focus-visible:outline-none focus-visible:border-[--glass-border-focus] focus-visible:shadow-[--glass-shadow-hover,--glass-glow] focus-visible:bg-[--glass-bg]",
          // Hover state: subtle highlight
          "hover:border-[--glass-border-hover] hover:bg-[--glass-bg]/50",
          // Placeholder styling
          "placeholder:text-muted-foreground/60",
          // File input styling
          "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
          // Disabled state: glass-disabled appearance
          "disabled:glass-disabled disabled:cursor-not-allowed",
          // Accessibility
          "aria-[invalid]:border-destructive aria-[invalid]:focus-visible:shadow-red-500/20",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
