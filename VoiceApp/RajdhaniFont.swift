//
//  RajdhaniFont.swift
//  VoiceApp
//
//  Created for consistent Rajdhani font usage
//

import SwiftUI

extension Font {
    static func rajdhani(_ weight: RajdhaniWeight, size: CGFloat) -> Font {
        return .custom(weight.fontName, size: size)
    }
}

enum RajdhaniWeight {
    case light
    case regular
    case medium
    case semiBold
    case bold
    
    var fontName: String {
        switch self {
        case .light:
            return "Rajdhani Light"
        case .regular:
            return "Rajdhani Regular"
        case .medium:
            return "Rajdhani Medium"
        case .semiBold:
            return "Rajdhani SemiBold"
        case .bold:
            return "Rajdhani Bold"
        }
    }
}

// Predefined common font styles
extension Font {
    static let rajdhaniTitle = Font.rajdhani(.bold, size: 40)
    static let rajdhaniLargeTitle = Font.rajdhani(.semiBold, size: 32)
    static let rajdhaniHeadline = Font.rajdhani(.semiBold, size: 18)
    static let rajdhaniBody = Font.rajdhani(.regular, size: 16)
    static let rajdhaniCaption = Font.rajdhani(.regular, size: 14)
    static let rajdhaniFootnote = Font.rajdhani(.light, size: 12)
} 