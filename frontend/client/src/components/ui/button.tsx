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
          // Primary button: glass effect with blue background and glow on hover
          "glass bg-primary/90 text-primary-foreground border-primary/30 " +
          "hover:bg-primary hover:shadow-[--glass-shadow-hover,--glass-glow] hover:scale-[1.02] hover:border-[--glass-border-hover] " +
          "active:scale-[0.98] active:shadow-[--glass-shadow-active] " +
          "backdrop-blur-md",
        destructive:
          // Destructive button: glass effect with red background
          "glass bg-destructive/90 text-destructive-foreground border-destructive/30 " +
          "hover:bg-destructive hover:shadow-[--glass-shadow-hover] hover:shadow-red-500/20 hover:scale-[1.02] " +
          "active:scale-[0.98] active:shadow-[--glass-shadow-active] " +
          "backdrop-blur-md",
        outline:
          // Outline button: subtle glass effect with transparent background
          "glass-light bg-transparent border-[--glass-border] " +
          "hover:bg-[--glass-bg-hover] hover:border-[--glass-border-hover] hover:shadow-[--glass-shadow-hover,--glass-glow] hover:scale-[1.02] " +
          "active:bg-[--glass-bg-active] active:scale-[0.98] active:shadow-none",
        secondary:
          // Secondary button: glass effect with muted background
          "glass bg-secondary/80 text-secondary-foreground border-secondary/40 " +
          "hover:bg-secondary hover:border-[--glass-border-hover] hover:shadow-[--glass-shadow-hover] hover:scale-[1.02] " +
          "active:scale-[0.98] active:shadow-[--glass-shadow-active] " +
          "backdrop-blur-md",
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
