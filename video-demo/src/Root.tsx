import { Composition } from "remotion";
import { DemoVideo } from "./DemoVideo";

export const RemotionRoot = () => {
  return (
    <Composition
      id="MedSignalDemo"
      component={DemoVideo}
      durationInFrames={2700}
      fps={30}
      width={3840}
      height={2160}
    />
  );
};
