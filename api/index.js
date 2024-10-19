#! /usr/bin/env node 
const { loadImage } = require('@napi-rs/canvas');
const url = require('url')
const fetch = require('node-fetch')
const { drawRoute } = require('./helpers')
const sharp = require('sharp');
const fs = require('node:fs');

const getMap = async (liveloxUrl) => {
    console.log("Livelox downloader")
    console.log(`fetching: ${liveloxUrl}`)
    let classId = ''
    try {
        classId = url.parse(liveloxUrl, true).query.classId
    } catch (e) {
        return 'no class id provided'
    }
    console.log(`classId: ${classId}`);
    let data = {}
    try {
        const res = await fetch("https://www.livelox.com/Data/ClassInfo", {
            "headers": {
                "accept": "application/json",
                "content-type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            "body": JSON.stringify({
                "classIds":[classId],
                "courseIds":null,
                "relayLegs":[],
                "relayLegGroupIds":[],
                "includeMap":true,
                "includeCourses":true,
                "skipStoreInCache":false
            }),
            "method": "POST"
        });
        data = await res.json()
    } catch (e) {
        return 'could not reach livelox server'
    }
    const eventData = data.general
    const blobUrl = eventData?.classBlobUrl
    console.log(`blobUrl: ${blobUrl}`)
    if (!blobUrl) {
        return 'cannot not figure blob url'
    }
    let blobData = null
    try {
        const res = await fetch(blobUrl, {
            "headers": {
                "accept": "application/json",
                "content-type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            }
        });
        blobData = await res.json()
    } catch (e) {
        return 'could not reach blob url'
    }

    let mapUrl, mapBound, mapResolution, route, mapName
    try {
        mapData = blobData.map
        mapUrl = mapData.url;
        mapBound = mapData.boundingQuadrilateral.vertices
        mapResolution = mapData.resolution
        route = blobData.courses.map((c) => c.controls)
        mapName = mapData.name
    } catch (e) {
        return 'could not parse livelox data'
    }
    try {
        const mapImg = await loadImage(mapUrl)
        const [outCanvas, bounds] = drawRoute(mapImg, mapBound, route, mapResolution)
        const imgBlob = outCanvas.toBuffer('image/png')
        const outImgBlob = await sharp(imgBlob).webp().toBuffer()
        let buffer
        let mime
        let filename
        buffer = outImgBlob
        mime = 'image/webp'
        filename = `${mapName}_${bounds[3].lat}_${bounds[3].lon}_${bounds[2].lat}_${bounds[2].lon}_${bounds[1].lat}_${bounds[1].lon}_${bounds[0].lat}_${bounds[0].lon}_.jpeg`
        fs.writeFile(filename.replace(/\\/g, '_').replace(/"/g, '\\"'), buffer, err => {
            if (err) {
              console.error(err);
            } else {
              return "file written successfully";
            }
        });
    } catch (e) {
        return 'Something went wrong... ' + e.message
    }
}

const get = async () => {
    console.log(await getMap("https://www.livelox.com/Viewer/Lillomarka-Nord-Sor/Herrer-15km?classId=862192&tab=player"))
}

get();
