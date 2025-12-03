import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  // Base styles: layout, typography, accessibility, and glass transition
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium " +
  // Glass interactive effects: smooth transitions with cubic-bezier easing
  "transition-all duration-200 ease-out " +
  // Focus state: glass glow effect with blue border
  "focus-visible:outline-none focus-visible:border-[--glass-border-focus] focus-visible:shadow-[--glass-shadow-hover,--glass-glow-strong] " +
  // Disabled state: glass-disabled appearance
  "disabled:glass-disabled " +
  // SVG icon sizing
  "[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 " +
  // Keyboard navigation support (aria-label required for icon buttons)
  "aria-[label]:cursor-pointer",
  {
    variants: {
      variant: {
        default:
          // Primary button: solid blue background with glow on hover
          // NOTE: Don't use 'glass' class here - it overrides bg-primary with white in light mode
          "bg-primary text-primary-foreground border border-primary/30 shadow-md " +
          "hover:bg-primary/90 hover:shadow-lg hover:shadow-blue-500/30 hover:scale-[1.02] hover:border-blue-400/50 " +
          "active:scale-[0.98] active:shadow-md " +
          "backdrop-blur-sm",
        destructive:
          // Destructive button: solid red background with glow on hover
          "bg-destructive text-destructive-foreground border border-destructive/30 shadow-md " +
          "hover:bg-destructive/90 hover:shadow-lg hover:shadow-red-500/30 hover:scale-[1.02] " +
          "active:scale-[0.98] active:shadow-md " +
          "backdrop-blur-sm",
        outline:
          // Outline button: subtle glass effect with transparent background
          "glass-light bg-transparent border-[--glass-border] " +
          "hover:bg-[--glass-bg-hover] hover:border-[--glass-border-hover] hover:shadow-[--glass-shadow-hover,--glass-glow] hover:scale-[1.02] " +
          "active:bg-[--glass-bg-active] active:scale-[0.98] active:shadow-none",
        secondary:
          // Secondary button: solid muted background
          "bg-secondary text-secondary-foreground border border-secondary/40 shadow-sm " +
          "hover:bg-secondary/90 hover:border-slate-400/50 hover:shadow-md hover:scale-[1.02] " +
          "active:scale-[0.98] active:shadow-sm " +
          "backdrop-blur-sm",
        ghost:
          // Ghost button: minimal glass effect, appears on hover
          "border-transparent bg-transparent " +
          "hover:glass-light hover:bg-[--glass-bg] hover:border-[--glass-border] hover:shadow-[--glass-shadow] hover:scale-[1.02] " +
          "active:scale-[0.98] active:bg-[--glass-bg-active]",
        link:
          // Link button: no glass effect, just underline
          "text-primary underline-offset-4 hover:underline hover:text-primary/80 active:text-primary/60",
      },
      size: {
        default: "min-h-9 px-4 py-2",
        sm: "min-h-8 rounded-md px-3 text-xs",
        lg: "min-h-10 rounded-md px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
