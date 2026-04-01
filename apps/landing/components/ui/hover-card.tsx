"use client"

import * as React from "react"
import { PreviewCard as HoverCardPrimitive } from "@base-ui/react/preview-card"

import { cn } from "@/lib/utils"

function HoverCard({ ...props }: HoverCardPrimitive.Root.Props) {
  return <HoverCardPrimitive.Root data-slot="hover-card" {...props} />
}

function HoverCardTrigger({
  className,
  ...props
}: HoverCardPrimitive.Trigger.Props) {
  return (
    <HoverCardPrimitive.Trigger
      data-slot="hover-card-trigger"
      className={cn("cursor-pointer", className)}
      render={<span />}
      {...props}
    />
  )
}

function HoverCardContent({
  className,
  align = "center",
  alignOffset = 0,
  side = "bottom",
  sideOffset = 4,
  ...props
}: HoverCardPrimitive.Popup.Props &
  Pick<
    HoverCardPrimitive.Positioner.Props,
    "align" | "alignOffset" | "side" | "sideOffset"
  >) {
  return (
    <HoverCardPrimitive.Portal>
      <HoverCardPrimitive.Positioner
        align={align}
        alignOffset={alignOffset}
        side={side}
        sideOffset={sideOffset}
        className="isolate z-50"
      >
        <HoverCardPrimitive.Popup
          data-slot="hover-card-content"
          className={cn(
            "z-50 w-64 origin-(--transform-origin) rounded-lg bg-popover p-3 text-sm text-popover-foreground shadow-md ring-1 ring-foreground/10 outline-hidden duration-100 data-[side=bottom]:slide-in-from-top-2 data-[side=inline-end]:slide-in-from-left-2 data-[side=inline-start]:slide-in-from-right-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95",
            className
          )}
          {...props}
        />
      </HoverCardPrimitive.Positioner>
    </HoverCardPrimitive.Portal>
  )
}

export { HoverCard, HoverCardTrigger, HoverCardContent }
