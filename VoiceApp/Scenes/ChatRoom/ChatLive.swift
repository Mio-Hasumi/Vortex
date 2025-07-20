//
//  ChatLive.swift
//  VoiceApp
//
//  Created by Amedeo Ercole on 7/19/25.
//

import SwiftUI

struct HashtagScreen: View {
    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            Image("sidebar")
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: 50, height: 204)
                .shadow(color: .white, radius: 12)
                .padding(.top, -120)
                .padding(.leading, 4)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)

            Image("orb")
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: 170, height: 170)
                .overlay(
                    LinearGradient(
                        gradient: Gradient(stops: [
                            .init(color: .clear,                   location: 0.0),
                            .init(color: Color.black.opacity(0.4), location: 0.3),
                            .init(color: Color.black.opacity(0.7), location: 1.0)
                        ]),
                        startPoint: .top, endPoint: .bottom
                    )
                )
                .overlay(
                    RadialGradient(
                        gradient: Gradient(colors: [.clear, Color.black.opacity(0.5)]),
                        center: .center, startRadius: 0, endRadius: 85
                    )
                )
                .padding(.top, 8)
                .padding(.trailing, 8)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topTrailing)

            Text("Let's talk about #psgvschelsea")
                .font(.custom("Rajdhani", size: 40))
                .foregroundColor(.white)
                .padding(.bottom, 150)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottom)

            ZStack {
                CirclePic(asset: "profile1")
                    .offset(x: -100, y: -100)

                CirclePic(asset: "profile2")
                    .shadow(color: .white.opacity(0.5), radius: 15, x: 0, y: 0)
                    .offset(x: 100, y: 0)

                CirclePic(asset: "profile3")
                    .offset(x: -100, y: 70)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
            .padding(.bottom, 140)

            Image("pullhandle")
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: 120, height: 50)
                .shadow(color: Color.white.opacity(0.25), radius: 2)
                .offset(y: 38)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottom)

            Image("Xcircle")
                .frame(width: 57, height: 5)
                .offset(y: 320)
        }
    }
}

private struct CirclePic: View {
    let asset: String
    var body: some View {
        Image(asset)
            .resizable()
            .aspectRatio(contentMode: .fill)
            .frame(width: 120, height: 120)
            .clipShape(Circle())
            .shadow(radius: 3)
    }
}

#Preview { HashtagScreen() }
