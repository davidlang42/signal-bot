function doEmail(e) {
  const title = e.parameter.title;
  if (!title) return doError(e, "No title set for email.");
  const html = e.parameter.html;
  const msg = e.parameter.msg;
  if (html) {
    GmailApp.sendEmail(EMAIL_ADDRESS, title, "", convertInlineImagesToBlobs(html))
  } else {
    if (!msg) msg = "";
    GmailApp.sendEmail(EMAIL_ADDRESS, title, msg)
  }
  return doSuccess("Email sent.");
}

//https://www.labnol.org/gmail-base64-images-231026
function convertInlineImagesToBlobs(htmlBody) {
  const inlineImages = {};

  // Find all base64 image tags in the html message.
  const base64ImageTags = htmlBody.match(/<img src="data:image\/(png|jpeg|gif);base64,([^"]+)"[^>]*>/gm) || [];

  base64ImageTags.forEach((base64ImageTag) => {
    // Extract the base64-encoded image data from the tag.
    const [, format, base64Data] = base64ImageTag.match(/data:image\/(png|jpeg|gif);base64,([^"]+)/);

    // Convert the base64 data to binary.
    const imageByte = Utilities.base64Decode(base64Data);

    // Create a blob containing the image data.
    const imageName = Utilities.getUuid();
    const imageBlob = Utilities.newBlob(imageByte, `image/${format}`, imageName);

    // Replace the base64 image tag with cid: image tag.
    const newImageTag = base64ImageTag.replace(/src="[^"]+"/, `src="cid:${imageName}"`);
    htmlBody = htmlBody.replace(base64ImageTag, newImageTag);

    inlineImages[imageName] = imageBlob;
  });

  return {
    htmlBody: htmlBody,
    inlineImages: inlineImages
  };
}