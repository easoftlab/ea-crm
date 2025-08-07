# Sound Files for Enhanced Chat Features

This directory should contain the following audio files for the enhanced chat system:

## Required Files

1. **notification.wav** - General notification sound
2. **message.wav** - New message notification sound
3. **mention.wav** - Mention notification sound (different tone for mentions)

## File Specifications

- **Format**: WAV (for maximum browser compatibility)
- **Duration**: 1-3 seconds each
- **Size**: Keep under 100KB each for fast loading
- **Quality**: 44.1kHz, 16-bit recommended

## Recommended Sounds

- **notification.wav**: Short, gentle chime or bell sound
- **message.wav**: Slightly different chime for new messages
- **mention.wav**: More attention-grabbing sound for mentions (e.g., higher pitch or different tone)

## Implementation Notes

- Files are referenced in the HTML templates
- Used by the enhanced chat system for audio feedback
- Fallback to silent operation if files are missing
- Users can disable sounds in their browser settings

## Creating Sound Files

You can create these sound files using:
- Online sound generators
- Audio editing software
- Free sound libraries (ensure proper licensing)
- Text-to-speech for simple tones

## Browser Compatibility

- Chrome, Firefox, Safari, Edge support WAV files
- Mobile browsers may have different autoplay policies
- Users must interact with the page before sounds can play 