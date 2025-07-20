//
//  Welcome.swift
//  VoiceApp
//
//  Created by Amedeo Ercole on 7/18/25.
//

import SwiftUI

struct Welcome: View {
    var body: some View {
        ZStack {
            // Orb
            Image("orb")
                .resizable()
                .aspectRatio(contentMode: .fill)
                .frame(width: 288, height: 289)
                .clipped()
                .shadow(radius: 4.7)
            
            Text("VORTEX")
                .font(.rajdhaniTitle)
                .foregroundColor(.white)
                .shadow(radius: 4)
                .offset(y: -0.5)
        }
        .frame(width: 450, height: 930)
        .background(Color.black)
        .cornerRadius(39)
    }
}

#Preview {
    Welcome()
}

