#Pulling node image
FROM node:11 as node

#Setting work directory
WORKDIR /app

#Copying application files
COPY ./badgr-ui .

#Compiling code
# RUN npm ci
RUN npm install
# RUN ng build --prod

#Setting up environment
# ARG NG_ENV=production

#Preparing build
RUN npm run ng build --prod
# -- --configuration=$NG_ENV


#Creating run time environment
FROM nginx:alpine

COPY ./badgr-ui/nginx.conf /etc/nginx/nginx.conf
COPY --from=node /app/dist /usr/share/nginx/html