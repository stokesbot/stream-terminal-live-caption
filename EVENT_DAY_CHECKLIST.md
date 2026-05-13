## Event-Day Checklist — June 5th

### Pre-Event (Night Before or Morning Of)

- [ ] Laptop charged / plugged in
- [ ] USB audio interface tested with mixer
- [ ] OS default recording device = USB audio interface
- [ ] `app.py` running, health check passes (`curl http://localhost:5000/health`)
- [ ] Chrome open at `http://localhost:5000/`, fullscreen, HDMI to TV
- [ ] TV input set to correct HDMI port
- [ ] Internet connection verified at venue (test with `curl https://portal.azure.com`)
- [ ] Backup: Local WiFi hotspot / phone tethering ready

### Audio Setup (On-Site)

- [ ] Mixer line-out → USB interface → Laptop confirmed
- [ ] Do a 30-second Hungarian speech test (any colleague speaking)
- [ ] Verify English captions appear on TV within ~1 second
- [ ] Check caption readability from audience seating position

### Contingency

- [ ] If internet fails: switch to phone tethering immediately
- [ ] If captions fail entirely: have English summary slides ready as fallback
- [ ] Keep Azure Portal open in another tab to monitor Speech resource status

### Post-Event

- [ ] Export Azure usage to verify cost
- [ ] Archive `app.py` + config for future events
- [ ] Note any audio quality issues or latency observations for refinement
