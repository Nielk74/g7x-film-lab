# Install the looks on a Canon G7 X Mark III

Use the ready-made **`.pf3` profiles** in the release download. No Python, LUT conversion or SD-card preparation is required for the camera installation.

**Camera status:** the PF3 files carry the authored look as a 33³ color table. Canon's offline G7 X Mark III compiler consumes that table. Physical registration and camera-produced JPEG appearance have not yet been tested, so these camera profiles remain experimental. The steps below describe Canon's supported registration workflow.

The camera has **three User Defined slots**. Keep any three of the five looks on the camera and swap one later through the same procedure. The `.cube` files are for photo/video editors; select the `.pf3` files when loading the camera.

## 1. Get the profiles and Canon's registration app

Download the project's latest release ZIP, extract it, and leave its `profiles` folder somewhere easy to find.

Install **Canon Picture Style File Registration Tool** once:

- [Download for Mac](https://sg.canon/en/support/0200746802)
- [Download for Windows](https://sg.canon/en/support/0200746702)

Download from Canon's page and follow its installer. The registration tool is a separate application from Picture Style Editor. Picture Style Editor is optional. Use the supplied PF3 directly in the registration tool for the camera upload.

On a Mac, Canon's installed application is under **Applications → Canon Utilities → Picture Style File Registration Tool**. On Windows, search the Start menu for **Picture Style File Registration Tool**.

Canon lists the G7 X Mark III among the registration tool's [supported cameras](https://app.ssw.imaging-saas.canon/app/en/pse.html). Its Windows release supports Windows 10/11. Its Mac 1.1.0 release lists macOS 13/14/15 and native Apple Silicon support. The native Picture Style parser was tested separately on macOS 26.4.1; that does **not** establish registration-tool USB compatibility on macOS 26. If the tool cannot detect the camera on that OS, use a computer running one of Canon's listed versions.

## 2. Connect the camera

1. Use a USB-C **data cable** between the camera and computer. Some charging cables cannot carry data.
2. Turn on the camera and choose a normal creative still-photo mode such as **P**.
3. Open **Picture Style File Registration Tool**. If another Canon camera-connection application is running, quit that application before reopening the registration tool. The shipped registration tool explicitly rejects a conflicting Canon connection application.

Wait for the G7 X Mark III to appear in the connected-camera list. If it does not appear, try a direct USB connection, a different data cable, and the supported OS check above. A file copied onto the memory card will not register itself as a Picture Style.

## 3. Register one look

These labels were recovered from the shipped **Windows 1.1.0.4** application. Mac wording can vary; follow the equivalent camera, slot and file controls.

1. Select the camera under **Supported cameras connected via USB**, then click **Register Picture Style File**.
2. Choose **User Def. 1**, **User Def. 2** or **User Def. 3**. Pick a slot you are happy to replace. Keep the original `.pf3` file for any look you may want to restore later.
3. Click that slot's **folder button** and select the desired `.pf3` from the release's `profiles` folder.
4. Click **Register**.
5. Wait for the completion message: **Registration of the Picture Style file is complete.**

Repeat for up to three looks. Replacing a slot changes the profile assigned to that slot; it does not add a fourth slot.

If the app says that the file version or shooting mode is unsupported, stop and record the exact message, camera firmware version, OS and registration-tool version. Do not substitute an experimental EOS uploader. The release includes a clear distinction between offline profile validation and physical camera validation.

## 4. Select the look and shoot

Disconnect the USB cable after registration completes. On the camera, open **Picture Style** from the shooting/Quick Control controls and choose the **User Def.** slot you just registered. The G7 X Mark III manual covers Picture Styles on printed pages 142–147.

For the first comparison:

- Shoot **RAW + JPEG** so you retain the original capture alongside the styled JPEG.
- Use fixed white balance and exposure for the comparison shots. A neutral daylight white balance is a useful starting point in daylight.
- Leave the profile's additional contrast, saturation and color-tone adjustments at their supplied values initially.
- Photograph skin, a gray/white object, foliage or blue sky, and a bright highlight. Review the actual camera JPEGs before changing the recipe.

The film number in a look's name is its reference stock's speed, **not** a requirement to set the digital camera to that ISO. Use the camera ISO appropriate to your exposure.

## Using the LUTs in an editor

The `.cube` files have the input/output color-space assumptions documented with the pack. Apply them once at the intended stage of your editing pipeline. The desktop CUBEs use a 65³ grid; the PF3 camera table samples the same look on Canon's 33³ grid. The PF3 also contains a polynomial/curve approximation for Canon's desktop preview engine, which follows a different path from camera-table compilation. Apply either look once; a styled camera JPEG should not receive the same desktop LUT again.

A pointwise color LUT carries color and tone. It does not add real film grain, halation, lens diffusion or film resolution. The release's visual comparisons and validation notes describe what was actually measured.

## What has been tested

Canon's **actual PSE 1.33.10 native parser** accepted the neutral calibration and all five final PF3s, including full table hash readback. [Canon's offline camera compiler](../research/canon-camera-compiler-validation.json) also compiled all five full color tables for G7 X Mark III model ID `0x808`, producing distinct color data. All five profiles changed the output of Canon's separate desktop RAW engine on a public G7 X Mark III RAW. [Actual Canon renders](../examples/canon-native/) and [the measured validation report](../research/canon-native-validation.json) are included.

Separate positive controls established two paths. Canon's offline compiler for G7 X Mark III model ID `0x808` produces different camera data for identity and deliberately black dense tables; changing only the preview matrix leaves that camera data unchanged. Canon's desktop RAW renderer instead uses the parametric curve/matrix representation. The supplied native-render examples measure that desktop approximation, and are not a camera-table or real-film accuracy measurement.

See [the retained installation evidence](../research/canon-install-evidence.json) for the exact software, controls and limits, and the pack's quality report for final-look validation. These are offline software tests. No physical camera was connected or written. The registration-tool labels above come from shipped application resources; its Windows GUI was not executed on this Mac.

## Official references

- [Canon supported products, PF2/PF3 workflow and PowerShot registration tool](https://app.ssw.imaging-saas.canon/app/en/pse.html)
- [Mac tool installation, application location and supported OS versions](https://sg.canon/en/support/0200746802)
- [Windows tool installation and supported OS versions](https://sg.canon/en/support/0200746702)
- [G7 X Mark III Advanced User Guide](https://gdlp01.c-wss.com/gds/8/0300035728/07/psg7x-mk3-ug7-en.pdf), printed pages 142–147
- [Canon's PF3/PF2 save-format notes](https://cam.start.canon/en/S004/manual/html/UG-04_Saving_0020.html)
