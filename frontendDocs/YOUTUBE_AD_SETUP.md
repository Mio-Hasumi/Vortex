# YouTube Ad Integration for Waiting Room

## Overview
The waiting room now includes a YouTube video ad that plays when users enter the waiting room and automatically disappears when:
1. The video ends naturally
2. A match is found
3. The user manually closes the ad
4. A timeout occurs (configurable)

## Configuration

### Changing the YouTube Video
To change the YouTube video that plays as an ad, edit the `APIConfig.swift` file:

```swift
// MARK: - YouTube Ad Configuration
static let youtubeAdVideoId = "YOUR_VIDEO_ID_HERE" // Change this to your desired ad video
static let youtubeAdTimeoutSeconds = 30 // Auto-hide timeout if video doesn't end properly
```

### How to Get a YouTube Video ID
1. Go to the YouTube video you want to use
2. Copy the video ID from the URL: `https://www.youtube.com/watch?v=VIDEO_ID_HERE`
3. Replace `YOUR_VIDEO_ID_HERE` with the actual video ID

### Example
For the video `https://www.youtube.com/watch?v=dQw4w9WgXcQ`, the video ID would be `dQw4w9WgXcQ`.

## Features

### Automatic Behavior
- **Autoplay**: Video starts playing immediately when user enters waiting room
- **Forced viewing**: Users cannot leave the waiting room until ad is complete
- **Auto-hide**: Video disappears when it ends naturally
- **Match detection**: Video hides immediately when a match is found
- **Timeout fallback**: Video hides after 30 seconds (configurable) if no end event is detected

### User Controls
- **No skip option**: Users must watch the ad to completion
- **Video controls**: Standard YouTube player controls are available
- **Fullscreen**: Users can enter fullscreen mode if desired
- **Timer display**: Shows remaining time until ad completion

### Visual Design
- **Responsive**: Video adapts to different screen sizes
- **Centered**: Video is centered on screen with proper padding
- **Rounded corners**: Video has rounded corners for modern appearance
- **Sponsored label**: Clear "Sponsored Content" label at bottom

## Technical Implementation

### Components
- `YouTubeVideoAd`: SwiftUI wrapper around WKWebView for YouTube embedding
- `APIConfig.youtubeAdVideoId`: Centralized configuration for video ID
- `APIConfig.youtubeAdTimeoutSeconds`: Configurable timeout duration

### Integration Points
- **Waiting Room**: `UserVoiceTopicMatchingView` in `UV-TM.swift`
- **State Management**: Uses `@State private var showYouTubeAd` to control visibility
- **Animation**: Smooth fade and scale transitions when showing/hiding

### WebView Features
- **YouTube API Integration**: Uses YouTube IFrame API for event handling
- **Message Handling**: Communicates video end events back to SwiftUI
- **Autoplay Support**: Configured for immediate playback
- **Mobile Optimized**: Responsive design for mobile devices

## Customization Options

### Video Parameters
You can modify the YouTube embed URL parameters in the HTML string:

```html
src="https://www.youtube.com/embed/VIDEO_ID?autoplay=1&controls=1&rel=0&showinfo=0&modestbranding=1&playsinline=1&enablejsapi=1"
```

Available parameters:
- `autoplay=1`: Start video automatically
- `controls=1`: Show video controls
- `rel=0`: Don't show related videos
- `showinfo=0`: Hide video info
- `modestbranding=1`: Minimal YouTube branding
- `playsinline=1`: Play inline on mobile
- `enablejsapi=1`: Enable YouTube API

### Styling
The video container styling can be modified in the CSS section:

```css
.video-container {
    position: relative;
    width: 100%;
    height: 100%;
    max-width: 400px;  /* Change max width */
    max-height: 300px; /* Change max height */
}
```

### Timeout Duration
Change the auto-hide timeout in `APIConfig.swift`:

```swift
static let youtubeAdTimeoutSeconds = 45 // Change to desired seconds
```

## Best Practices

### Video Selection
- Choose short videos (15-30 seconds) for better user experience
- Use high-quality, engaging content
- Ensure videos are appropriate for your audience
- Consider using videos that match your app's theme

### User Experience
- The ad should not interfere with the core functionality
- Users must watch the ad to completion before proceeding
- Video automatically hides when match is found
- Smooth transitions maintain app flow
- Timer display shows progress and remaining time

### Performance
- Video loads asynchronously
- WebView is optimized for mobile performance
- Minimal impact on app memory usage
- Cleanup occurs when view disappears

## Troubleshooting

### Video Not Playing
1. Check that the video ID is correct
2. Ensure the video is publicly available
3. Verify internet connectivity
4. Check if video has embedding restrictions

### Ad Not Hiding
1. Check timeout configuration
2. Verify YouTube API is loading properly
3. Check console for JavaScript errors
4. Ensure message handlers are properly set up

### Performance Issues
1. Use shorter videos for better performance
2. Consider video quality settings
3. Monitor memory usage
4. Test on different devices

## Future Enhancements

### Potential Improvements
- **Multiple videos**: Rotate between different ad videos
- **Analytics**: Track ad view completion rates
- **A/B testing**: Test different video content
- **Targeting**: Show different ads based on user preferences
- **Scheduling**: Show ads at specific times or conditions

### Integration Possibilities
- **Ad networks**: Integrate with ad serving platforms
- **Revenue tracking**: Track ad revenue and performance
- **User preferences**: Allow users to opt out of ads
- **Premium features**: Hide ads for premium users 